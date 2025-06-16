# AI Provider System Guide

## Overview

The Doubt Solver application now supports multiple AI providers with dynamic switching capabilities. You can easily switch between Google Gemini, OpenRouter, and OpenAI based on your needs and availability.

## Supported Providers

| Provider | Description | Status |
|----------|-------------|--------|
| **Gemini** | Google's Gemini 2.0 Flash | ✅ **DEFAULT** |
| **OpenRouter** | OpenRouter proxy service | ✅ Available |
| **OpenAI** | Direct OpenAI API | ✅ Available |

## Quick Start

### 1. Current Configuration

The system is currently configured to use **Gemini** as the default provider. All requests will automatically go to Gemini instead of OpenRouter.

### 2. Environment Variables

Your environment file (`resources/doubtsolver.env`) now includes:

```bash
# AI Provider Configuration
AI_PROVIDER="gemini"                    # Current provider: gemini, openrouter, or openai
GEMINI_API_KEY="AIzaSy..."             # Google Gemini API key
OPENAI_API_KEY="sk-or-v1-..."          # OpenRouter/OpenAI API key
```

### 3. Testing Providers

Use the AI Provider Manager to test and manage providers:

```bash
# List all providers and their status
python ai_provider_manager.py list

# Test current provider
python ai_provider_manager.py test

# Test specific provider
python ai_provider_manager.py test gemini "Your question here"

# Switch provider
python ai_provider_manager.py set gemini
```

## Detailed Usage

### Provider Management

#### Check Current Provider
```bash
python ai_provider_manager.py current
```

#### Switch Between Providers
```bash
# Switch to Gemini (recommended)
python ai_provider_manager.py set gemini

# Switch to OpenRouter
python ai_provider_manager.py set openrouter

# Switch to OpenAI
python ai_provider_manager.py set openai
```

#### Test All Providers
```bash
python ai_provider_manager.py test-all
```

### API Differences

#### Gemini API Format
- **Request Format**: Gemini uses a `contents` array with `parts`
- **Response Format**: Returns `candidates` with `content.parts[0].text`
- **Authentication**: API key passed as query parameter
- **Model**: `gemini-2.0-flash`

```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "Your prompt here"
        }
      ]
    }
  ]
}
```

#### OpenRouter API Format
- **Request Format**: OpenAI-compatible `messages` format
- **Response Format**: Standard OpenAI response format
- **Authentication**: Bearer token in headers
- **Model**: `openai/gpt-3.5-turbo`

```json
{
  "model": "openai/gpt-3.5-turbo",
  "messages": [{"role": "user", "content": "Your prompt here"}],
  "temperature": 0.7,
  "max_tokens": 1500
}
```

## Implementation Details

### Provider Architecture

The system uses a factory pattern with provider-specific implementations:

```python
# Provider selection
provider = AIServiceProvider.get_provider("gemini")

# Dynamic switching based on environment
current_provider = os.getenv("AI_PROVIDER", "gemini")
```

### Key Features

1. **Dynamic Provider Switching**: Change providers without code changes
2. **Provider-Specific Error Handling**: Each provider has tailored error handling
3. **Automatic Fallback**: Falls back to Gemini if provider is invalid
4. **Request/Response Translation**: Handles different API formats automatically
5. **Comprehensive Logging**: Provider-specific logging for debugging

### Error Handling

Each provider handles common scenarios:
- **Authentication failures** (401)
- **Rate limiting** (429)
- **Server errors** (5xx)
- **Invalid responses**
- **Network timeouts**

## Migration Notes

### What Changed

1. **Default Provider**: Changed from OpenRouter to Gemini
2. **Configuration**: Added `AI_PROVIDER` and `GEMINI_API_KEY` environment variables
3. **API Service**: Completely rewritten to support multiple providers
4. **Error Messages**: Now include provider-specific information

### Backward Compatibility

- ✅ Existing OpenRouter integration still works
- ✅ All existing API endpoints remain unchanged
- ✅ No changes needed in frontend/client code
- ✅ Existing error handling patterns preserved

## Testing

### Unit Tests

Run the Gemini integration test:

```bash
python test_gemini.py
```

### Provider Manager Tests

```bash
# Test configuration
python ai_provider_manager.py list

# Test current provider
python ai_provider_manager.py test

# Test with custom prompt
python ai_provider_manager.py test gemini "Explain quantum computing"
```

### Integration Tests

The system automatically detects and tests provider configurations:

1. **Configuration Validation**: Checks API keys and settings
2. **Response Parsing**: Validates response format handling
3. **Error Scenarios**: Tests timeout and error conditions

## Troubleshooting

### Common Issues

#### Provider Not Configured
```
❌ Gemini configuration error: Gemini API key not configured
```
**Solution**: Add your API key to `resources/doubtsolver.env`

#### API Key Invalid
```
❌ Gemini service authentication failed
```
**Solution**: Verify your API key is correct and has proper permissions

#### Network Issues
```
❌ Network error after 2 attempts
```
**Solution**: Check internet connection and API service status

### Debug Commands

```bash
# Check all provider statuses
python ai_provider_manager.py list

# Test specific provider
python ai_provider_manager.py test gemini

# Check current configuration
python ai_provider_manager.py current
```

## Best Practices

### 1. Provider Selection

- **Use Gemini** for general usage (fast, cost-effective)
- **Use OpenRouter** for alternative models or backup
- **Use OpenAI** for direct OpenAI access

### 2. Error Handling

The system automatically handles provider failures and provides detailed error messages for debugging.

### 3. Monitoring

Monitor logs for provider-specific performance metrics:
```
INFO - Sending request to Gemini AI service
INFO - Gemini response received successfully (response_length: 1234)
```

## API Reference

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AI_PROVIDER` | Yes | Current provider | `gemini` |
| `GEMINI_API_KEY` | For Gemini | Google Gemini API key | `AIzaSy...` |
| `OPENAI_API_KEY` | For OpenRouter/OpenAI | API key | `sk-or-v1-...` |

### Provider-Specific Settings

#### Gemini
- **Base URL**: `https://generativelanguage.googleapis.com/v1beta`
- **Model**: `gemini-2.0-flash`
- **Authentication**: Query parameter
- **Rate Limits**: Per Google's policy

#### OpenRouter
- **Base URL**: `https://openrouter.ai/api/v1`
- **Model**: `openai/gpt-3.5-turbo`
- **Authentication**: Bearer token
- **Rate Limits**: Per OpenRouter's policy

---

## Summary

✅ **Gemini is now the default AI provider**
✅ **All requests automatically route to Gemini**
✅ **OpenRouter is available as backup**
✅ **Dynamic provider switching supported**
✅ **Comprehensive error handling and logging**
✅ **Backward compatibility maintained**

The system is ready for production use with Gemini as the primary AI provider! 