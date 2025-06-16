import asyncpg
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.db import db
from app.core.security import hash_password, verify_password, decode_access_token
from app.core.logging_config import get_logger, PerformanceLogger
from app.core.exceptions import (
    DatabaseError, 
    ValidationError, 
    AuthenticationError, 
    InvalidCredentialsError,
    RecordNotFoundError,
    RecordAlreadyExistsError,
    UserOperationError
)

logger = get_logger("user_services")
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: JWT token from Authorization header
        
    Returns:
        dict: User information (user_id, email, username)
        
    Raises:
        HTTPException: When authentication fails
    """
    
    try:
        token = credentials.credentials
        
        if not token:
            logger.warning("No token provided in authorization header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "MISSING_TOKEN",
                    "message": "Authentication token is required"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        print(token)
        # Decode JWT token
        payload = decode_access_token(token)
        print(payload)
        if not payload:
            logger.warning("Invalid or expired token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Invalid or expired authentication token"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Extract user info from token
        user_id = payload.get("user_id")
        
        if not user_id:
            logger.warning("Token missing user_id", extra={"payload": payload})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN_PAYLOAD",
                    "message": "Token is missing required user information"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Verify user still exists in database
        try:
            user = await get_user_by_id(user_id)
            
            logger.debug(
                "User authenticated successfully",
                extra={"user_id": user_id}
            )
            
            return {
                "user_id": user["id"],
                "email": user["email"],
                "username": user["username"]
            }
            
        except RecordNotFoundError:
            logger.warning(
                "Token references non-existent user",
                extra={"user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "USER_NOT_FOUND",
                    "message": "User account no longer exists"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during authentication: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "AUTHENTICATION_ERROR",
                "message": "An error occurred during authentication"
            }
        )

async def create_user(email: str, username: str, password: str):
    """
    Create a new user with comprehensive error handling
    
    Args:
        email: User's email address
        username: User's username
        password: User's plain text password (will be hashed)
        
    Returns:
        Database record of the created user
        
    Raises:
        ValidationError: When input validation fails
        RecordAlreadyExistsError: When email already exists
        DatabaseError: When database operation fails
    """
    
    # Input validation
    if not email or not email.strip():
        logger.error("Empty email provided")
        raise ValidationError(
            message="Email is required",
            details={"field": "email"}
        )
    
    if not username or not username.strip():
        logger.error("Empty username provided")
        raise ValidationError(
            message="Username is required",
            details={"field": "username"}
        )
    
    if not password or len(password) < 6:
        logger.error("Invalid password provided")
        raise ValidationError(
            message="Password must be at least 6 characters long",
            details={"field": "password", "min_length": 6}
        )
    
    # Sanitize inputs
    email = email.strip().lower()
    username = username.strip()
    
    logger.info(
        "Creating new user",
        extra={
            "email": email,
            "username": username
        }
    )
    
    try:
        with PerformanceLogger(logger, "create_user", email=email):
            pool = await db.get_pool()
            
            async with pool.acquire() as conn:
                # Check if email already exists
                try:
                    existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
                    if existing:
                        logger.warning(
                            "Attempt to create user with existing email",
                            extra={"email": email}
                        )
                        raise RecordAlreadyExistsError(
                            message="Email already registered",
                            details={"email": email}
                        )
                    
                    # Hash password
                    hashed_password = hash_password(password)
                    
                    # Create user
                    row = await conn.fetchrow(
                        """
                        INSERT INTO users (email, username, password) VALUES ($1, $2, $3)
                        RETURNING id, email, username
                        """, 
                        email, username, hashed_password
                    )
                    
                    if not row:
                        logger.error("User creation failed - no row returned", extra={"email": email})
                        raise UserOperationError(
                            message="Failed to create user",
                            details={"email": email}
                        )
                    
                    logger.info(
                        "User created successfully",
                        extra={
                            "user_id": row["id"],
                            "email": email,
                            "username": username
                        }
                    )
                    
                    return row
                    
                except asyncpg.UniqueViolationError as e:
                    logger.warning(
                        f"Unique constraint violation during user creation: {e}",
                        extra={"email": email}
                    )
                    raise RecordAlreadyExistsError(
                        message="Email already registered",
                        details={"email": email, "db_error": str(e)}
                    )
                    
                except asyncpg.PostgresError as e:
                    logger.error(
                        f"PostgreSQL error creating user: {e}",
                        extra={"email": email, "error_code": e.sqlstate},
                        exc_info=True
                    )
                    raise DatabaseError(
                        message="Database error while creating user",
                        details={
                            "email": email,
                            "postgres_error": str(e),
                            "error_code": e.sqlstate
                        }
                    )
                    
    except (ValidationError, RecordAlreadyExistsError, UserOperationError, DatabaseError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error creating user: {e}",
            extra={"email": email},
            exc_info=True
        )
        raise UserOperationError(
            message="Unexpected error while creating user",
            details={"email": email, "error": str(e)}
        )


async def get_user_by_email(email: str):
    """Get user by email with error handling"""
    
    if not email or not email.strip():
        logger.error("Empty email provided for user lookup")
        raise ValidationError(
            message="Email is required",
            details={"field": "email"}
        )
    
    email = email.strip().lower()
    
    logger.debug("Looking up user by email", extra={"email": email})
    
    try:
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id, email, username, password FROM users WHERE email = $1", 
                email
            )
            
            if not user:
                logger.info("User not found by email", extra={"email": email})
                raise RecordNotFoundError(
                    message="User not found",
                    details={"email": email}
                )
            
            logger.debug("User found by email", extra={"email": email, "user_id": user["id"]})
            return user
            
    except RecordNotFoundError:
        raise
    except asyncpg.PostgresError as e:
        logger.error(
            f"PostgreSQL error looking up user by email: {e}",
            extra={"email": email},
            exc_info=True
        )
        raise DatabaseError(
            message="Database error while looking up user",
            details={"email": email, "postgres_error": str(e)}
        )
    except Exception as e:
        logger.error(
            f"Unexpected error looking up user by email: {e}",
            extra={"email": email},
            exc_info=True
        )
        raise DatabaseError(
            message="Unexpected error while looking up user",
            details={"email": email, "error": str(e)}
        )


async def get_user_by_id(user_id: int):
    """Get user by ID with error handling"""
    
    if not user_id or user_id <= 0:
        logger.error("Invalid user_id provided", extra={"user_id": user_id})
        raise ValidationError(
            message="Invalid user ID",
            details={"user_id": user_id}
        )
    
    logger.debug("Looking up user by ID", extra={"user_id": user_id})
    
    try:
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id, email, username FROM users WHERE id = $1", 
                user_id
            )
            
            if not user:
                logger.info("User not found by ID", extra={"user_id": user_id})
                raise RecordNotFoundError(
                    message="User not found",
                    details={"user_id": user_id}
                )
            
            logger.debug("User found by ID", extra={"user_id": user_id, "email": user["email"]})
            return user
            
    except RecordNotFoundError:
        raise
    except asyncpg.PostgresError as e:
        logger.error(
            f"PostgreSQL error looking up user by ID: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise DatabaseError(
            message="Database error while looking up user",
            details={"user_id": user_id, "postgres_error": str(e)}
        )
    except Exception as e:
        logger.error(
            f"Unexpected error looking up user by ID: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise DatabaseError(
            message="Unexpected error while looking up user",
            details={"user_id": user_id, "error": str(e)}
        )


async def update_user(user_id: int, email: str, username: str, password: str):
    pool = await db.get_pool()
    hashed = hash_password(password)
    row = await pool.fetchrow(
        """
        UPDATE users SET email = $1, username = $2, password = $3 WHERE id = $4
        RETURNING id, email, username
        """, email, username, hashed, user_id
    )
    if not row:
        raise HTTPException(status_code=500, detail="User update failed")
    return row

async def delete_user(user_id: int):
    pool = await db.get_pool()
    result = await pool.execute("DELETE FROM users WHERE id = $1", user_id)
    if result != "DELETE 1":
        raise HTTPException(status_code=404, detail="User not found or already deleted")
    return True

async def verify_user_credentials(email: str, password: str):
    """Verify user credentials with comprehensive error handling"""
    
    if not email or not email.strip():
        logger.error("Empty email provided for authentication")
        raise ValidationError(
            message="Email is required",
            details={"field": "email"}
        )
    
    if not password:
        logger.error("Empty password provided for authentication")
        raise ValidationError(
            message="Password is required",
            details={"field": "password"}
        )
    
    email = email.strip().lower()
    
    logger.info("Attempting user authentication", extra={"email": email})
    
    try:
        with PerformanceLogger(logger, "verify_credentials", email=email):
            pool = await db.get_pool()
            async with pool.acquire() as conn:
                user = await conn.fetchrow(
                    "SELECT id, email, username, password FROM users WHERE email = $1", 
                    email
                )
                
                if not user:
                    logger.warning("Authentication failed - user not found", extra={"email": email})
                    raise InvalidCredentialsError(
                        message="Incorrect email or password",
                        details={"email": email}
                    )
                
                if not verify_password(password, user["password"]):
                    logger.warning("Authentication failed - invalid password", extra={"email": email})
                    raise InvalidCredentialsError(
                        message="Incorrect email or password",
                        details={"email": email}
                    )
                
                logger.info(
                    "User authentication successful",
                    extra={"email": email, "user_id": user["id"]}
                )
                
                return user
                
    except InvalidCredentialsError:
        raise
    except asyncpg.PostgresError as e:
        logger.error(
            f"PostgreSQL error during authentication: {e}",
            extra={"email": email},
            exc_info=True
        )
        raise DatabaseError(
            message="Database error during authentication",
            details={"email": email, "postgres_error": str(e)}
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during authentication: {e}",
            extra={"email": email},
            exc_info=True
        )
        raise AuthenticationError(
            message="Unexpected error during authentication",
            details={"email": email, "error": str(e)}
        ) 