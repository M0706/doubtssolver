#!/usr/bin/env python3
"""
AI Provider Manager - Utility to manage and test AI providers dynamically
"""

import asyncio
import os
import sys
from dotenv import load_dotenv, set_key
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'resources', 'doubtsolver.env')
load_dotenv(dotenv_path=env_path)

from app.services.ai_service import get_ai_response, AIServiceProvider

class AIProviderManager:
    """Manage AI providers and test them"""
    
    PROVIDERS = {
        "gemini": "Google Gemini",
        "openrouter": "OpenRouter",
        "openai": "OpenAI"
    }
    
    def __init__(self):
        self.env_path = env_path
    
    def get_current_provider(self):
        """Get the currently configured provider"""
        return os.getenv("AI_PROVIDER", "gemini")
    
    def set_provider(self, provider_name: str):
        """Set the AI provider in the environment file"""
        if provider_name not in self.PROVIDERS:
            print(f"❌ Invalid provider: {provider_name}")
            print(f"Available providers: {', '.join(self.PROVIDERS.keys())}")
            return False
        
        # Update the environment file
        set_key(self.env_path, "AI_PROVIDER", provider_name)
        
        # Reload environment variables
        load_dotenv(dotenv_path=self.env_path, override=True)
        
        print(f"✅ AI provider set to: {provider_name} ({self.PROVIDERS[provider_name]})")
        return True
    
    def check_provider_config(self, provider_name: str = None):
        """Check if a provider is properly configured"""
        if provider_name is None:
            provider_name = self.get_current_provider()
        
        try:
            provider = AIServiceProvider.get_provider(provider_name)
            provider.validate_config()
            return True, f"✅ {provider.provider_name} is properly configured"
        except Exception as e:
            return False, f"❌ {provider_name} configuration error: {e}"
    
    async def test_provider(self, provider_name: str = None, prompt: str = None):
        """Test a specific provider with a sample prompt"""
        if provider_name is None:
            provider_name = self.get_current_provider()
        
        if prompt is None:
            prompt = "What is artificial intelligence? Explain in one sentence."
        
        print(f"\n🧪 Testing {provider_name} provider...")
        print(f"📝 Prompt: {prompt}")
        print("-" * 50)
        
        try:
            # Check configuration first
            is_configured, config_msg = self.check_provider_config(provider_name)
            if not is_configured:
                print(config_msg)
                return False
            
            # Make the API call
            response = await get_ai_response(prompt, provider_name=provider_name)
            
            print(f"✅ Response received ({len(response)} characters):")
            print(f"💬 {response}")
            print("-" * 50)
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            print("-" * 50)
            return False
    
    def list_providers(self):
        """List all available providers and their status"""
        print("\n📋 Available AI Providers:")
        print("=" * 50)
        
        current = self.get_current_provider()
        
        for provider_key, provider_name in self.PROVIDERS.items():
            is_current = "🎯 CURRENT" if provider_key == current else ""
            is_configured, config_msg = self.check_provider_config(provider_key)
            status = "✅ READY" if is_configured else "❌ NOT CONFIGURED"
            
            print(f"{provider_key:<12} | {provider_name:<15} | {status:<15} | {is_current}")
        
        print("=" * 50)
    
    async def test_all_providers(self, prompt: str = None):
        """Test all configured providers"""
        print("\n🔄 Testing all providers...")
        
        results = {}
        for provider_key in self.PROVIDERS.keys():
            is_configured, _ = self.check_provider_config(provider_key)
            if is_configured:
                results[provider_key] = await self.test_provider(provider_key, prompt)
            else:
                print(f"\n⏭️  Skipping {provider_key} (not configured)")
                results[provider_key] = False
        
        print(f"\n📊 Test Results Summary:")
        print("=" * 30)
        for provider, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{provider:<12} | {status}")
        print("=" * 30)

async def main():
    """Main CLI interface"""
    manager = AIProviderManager()
    
    if len(sys.argv) < 2:
        print("🤖 AI Provider Manager")
        print("=" * 50)
        print("Usage:")
        print("  python ai_provider_manager.py list")
        print("  python ai_provider_manager.py current")
        print("  python ai_provider_manager.py set <provider>")
        print("  python ai_provider_manager.py test [provider] [prompt]")
        print("  python ai_provider_manager.py test-all [prompt]")
        print()
        print("Examples:")
        print("  python ai_provider_manager.py set gemini")
        print("  python ai_provider_manager.py test gemini 'Explain machine learning'")
        print("  python ai_provider_manager.py test-all")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        manager.list_providers()
    
    elif command == "current":
        current = manager.get_current_provider()
        print(f"🎯 Current AI provider: {current} ({manager.PROVIDERS.get(current, 'Unknown')})")
        is_configured, config_msg = manager.check_provider_config(current)
        print(f"   {config_msg}")
    
    elif command == "set":
        if len(sys.argv) < 3:
            print("❌ Please specify a provider to set")
            print(f"Available providers: {', '.join(manager.PROVIDERS.keys())}")
            return
        
        provider = sys.argv[2].lower()
        manager.set_provider(provider)
    
    elif command == "test":
        provider = sys.argv[2].lower() if len(sys.argv) > 2 else None
        prompt = ' '.join(sys.argv[3:]) if len(sys.argv) > 3 else None
        
        await manager.test_provider(provider, prompt)
    
    elif command == "test-all":
        prompt = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        await manager.test_all_providers(prompt)
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main()) 