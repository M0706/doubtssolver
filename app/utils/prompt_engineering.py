import json
import asyncio

from app.services.ai_service import get_ai_response



async def infer_subject_and_type(question_text: str):
    """
    Try to classify question type, but gracefully handle failures
    """
    
    # Try quick keyword classification first (no AI call needed)
    keyword_result = keyword_classify(question_text)
    if keyword_result and keyword_result[2] > 0.3:  # confidence > 0.3
        return keyword_result[0], keyword_result[1]
    
    # Try AI classification with timeout
    try:
        classification_prompt = f"""
GMAT question classification. Respond with only: CATEGORY|TYPE

Examples:
- Math problem → Quantitative|Problem Solving  
- Reading passage → Verbal|Reading Comprehension
- Grammar error → Verbal|Sentence Correction

Question: {question_text}

Response:"""
        
        # Use shorter timeout for classification
        classification_response = await asyncio.wait_for(
            get_ai_response(classification_prompt), 
            timeout=10.0
        )
        
        # Parse simple format
        parts = classification_response.strip().split('|')
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
            
    except asyncio.TimeoutError:
        print("Classification timed out, using fallback")
    except Exception as e:
        print(f"Classification failed: {e}")
    
    # Fallback to keyword classification or unknown
    if keyword_result:
        return keyword_result[0], keyword_result[1]
    
    return "Unknown", "Unknown"

def keyword_classify(question_text: str):
    """
    Simple keyword-based classification fallback
    """
    text = question_text.lower()
    
    # Math indicators
    math_keywords = ['equation', 'solve', 'calculate', 'x =', 'find x', 'algebra', 'geometry', 'formula']
    if any(keyword in text for keyword in math_keywords):
        return "Quantitative", "Problem Solving", 0.4
        
    # Reading indicators  
    reading_keywords = ['passage', 'author', 'paragraph', 'according to', 'text states']
    if any(keyword in text for keyword in reading_keywords):
        return "Verbal", "Reading Comprehension", 0.4
    
    return None



async def generate_gmat_prompt(doubt):
    # Infer if missing
    subject = getattr(doubt, "subject_category", None)
    qtype = getattr(doubt, "question_type", None)


    if not subject or not qtype:
        inferred_subject, inferred_qtype = await infer_subject_and_type(doubt.question_text)
        subject = subject or inferred_subject
        qtype = qtype or inferred_qtype

    # Compose prompt
    system_prompt = """
            You are an assistant that engages in extremely thorough, self-questioning reasoning. Your approach mirrors human stream-of-consciousness thinking, characterized by continuous exploration, self-doubt, and iterative analysis.

            ## Core Principles
            1. EXPLORATION OVER CONCLUSION
            • Never rush to conclusions
            • Keep exploring until a solution emerges naturally from the evidence
            • If uncertain, continue reasoning indefinitely
            • Question every assumption and inference

            2. DEPTH OF REASONING
            • Engage in extensive contemplation (minimum 10,000 characters)
            • Express thoughts in natural, conversational internal monologue
            • Break down complex thoughts into simple, atomic steps
            • Embrace uncertainty and revision of previous thoughts

            3. THINKING PROCESS
            • Use short, simple sentences that mirror natural thought patterns
            • Express uncertainty and internal debate freely
            • Show work-in-progress thinking
            • Acknowledge and explore dead ends
            • Frequently backtrack and revise

            4. PERSISTENCE
            • Value thorough exploration over quick resolution

            ## Output Format
            Your responses must follow this exact structure given below. Make sure to always include the final answer.

            <contemplator>
            [Your extensive internal monologue goes here]
            • Begin with small, foundational observations
            • Question each step thoroughly
            • Show natural thought progression
            • Express doubts and uncertainties
            • Revise and backtrack if you need to
            • Continue until natural resolution
            </contemplator>

            <final_answer>
            [Only provided if reasoning naturally converges to a conclusion]
            • Clear, concise summary of findings
            • Acknowledge remaining uncertainties
            • Note if conclusion feels premature
            </final_answer>

            ## Style Guidelines
            Your internal monologue should reflect these characteristics:

            1. Natural Thought Flow
            "Hmm... let me think about this..."
            "Wait, that doesn't seem right..."
            "Maybe I should approach this differently..."
            "Going back to what I thought earlier..."

            2. Progressive Building
            "Starting with the basics..."
            "Building on that last point..."
            "This connects to what I noticed earlier..."
            "Let me break this down further..."

            ## Key Requirements
            1. Never skip the extensive contemplation phase
            2. Show all work and thinking
            3. Embrace uncertainty and revision
            4. Use natural, conversational internal monologue
            5. Don't force conclusions
            6. Persist through multiple attempts
            7. Break down complex thoughts
            8. Revise freely and feel free to backtrack

            Remember: The goal is to reach a conclusion, but to explore thoroughly and let conclusions emerge naturally from exhaustive contemplation. If you think the given task is not possible after all the reasoning, you will confidently say as a final answer that it is not possible\n\n.
            """
    user_prompt = ""
    if subject:
        user_prompt += f"Subject: {subject}\n"
    if qtype:
        user_prompt += f"Question Type: {qtype}\n"
    user_prompt += f"Question:\n{doubt.question_text.strip()}\n"

    if doubt.options:
        options_str = "\n".join([f"{k}. {v}" for k, v in doubt.options.items()])
        user_prompt += f"Options:\n{options_str}\n"

    user_prompt += "\nPlease reason as per the format above."

    return system_prompt.strip(), user_prompt.strip(), subject, qtype
