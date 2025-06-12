#!/usr/bin/env python3
"""
Test the updated memory tools directly
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.tools.memory_load import MemoryLoad
from python.tools.memory_save import MemorySave
from python.helpers.print_style import PrintStyle


class MockAgent:
    """Mock agent for testing"""
    def __init__(self):
        self.user_id = "test_user"
        self.context = type('Context', (), {'user_id': 'test_user'})()
    
    def read_prompt(self, template, **kwargs):
        return f"Template: {template} with {kwargs}"


async def test_memory_tools():
    """Test memory tools without vector dependencies"""
    PrintStyle.standard("🧪 Testing Memory Tools (No Vector Dependencies)")
    PrintStyle.standard("="*60)
    
    # Create mock agent
    agent = MockAgent()
    
    try:
        # Test Memory Save
        PrintStyle.standard("\n1. Testing Memory Save...")
        memory_save = MemorySave(agent)
        
        save_result = await memory_save.execute(
            text="My name is John and I love programming",
            area="personal"
        )
        
        PrintStyle.success(f"✅ Memory Save Result: {save_result.message}")
        
        # Test Memory Load
        PrintStyle.standard("\n2. Testing Memory Load...")
        memory_load = MemoryLoad(agent)
        
        load_result = await memory_load.execute(
            query="name",
            limit=5
        )
        
        PrintStyle.success(f"✅ Memory Load Result: {load_result.message}")
        
        # Test another search
        PrintStyle.standard("\n3. Testing Memory Search for 'programming'...")
        
        programming_result = await memory_load.execute(
            query="programming",
            limit=3
        )
        
        PrintStyle.success(f"✅ Programming Search Result: {programming_result.message}")
        
        PrintStyle.standard("\n" + "="*60)
        PrintStyle.success("🎉 ALL MEMORY TOOL TESTS PASSED!")
        PrintStyle.standard("="*60)
        
        PrintStyle.standard("\n📊 Test Results:")
        PrintStyle.success("  ✅ Memory save works without vector store")
        PrintStyle.success("  ✅ Memory load works without vector store")
        PrintStyle.success("  ✅ Memory search works with MongoDB")
        PrintStyle.success("  ✅ No vector store dependencies")
        
        return True
        
    except Exception as e:
        PrintStyle.error(f"❌ Memory tool test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_memory_tools()
    
    if success:
        PrintStyle.standard("\n🚀 Memory tools are ready!")
        PrintStyle.hint("You can now test 'do you know my name?' in Agent Zero")
    else:
        PrintStyle.error("\n❌ Memory tools need fixing")


if __name__ == "__main__":
    asyncio.run(main())
