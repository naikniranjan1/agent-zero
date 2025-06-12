"""
Simple Context Extension - Fallback for memory system
Provides basic context without complex dependencies
"""

from python.helpers.extension import Extension
from agent import LoopData
from python.helpers.print_style import PrintStyle


class SimpleContext(Extension):
    """Simple context provider without complex memory dependencies"""
    
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        """Provide simple context from recent conversation"""
        
        # Skip if no user message
        if not loop_data.user_message:
            return
        
        try:
            # Get the user's message
            user_query = loop_data.user_message.output_text() if loop_data.user_message else ""
            
            if not user_query.strip():
                return
            
            # Simple message classification
            query_lower = user_query.lower().strip()
            
            # Check if it's a simple greeting
            simple_greetings = ['hi', 'hey', 'hello', 'yo', 'thanks', 'thank you', 'ok', 'okay', 'yes', 'no']
            is_simple = any(greeting in query_lower for greeting in simple_greetings) or len(query_lower.split()) <= 3
            
            if is_simple:
                # For simple messages, just provide minimal context
                log_item = self.agent.context.log.log(
                    type="util",
                    heading="⚡ Fast response (simple message)",
                    temp=True
                )
                return
            
            # For other messages, provide recent conversation context
            log_item = self.agent.context.log.log(
                type="util",
                heading="📝 Adding conversation context",
            )
            
            # Get recent conversation history
            recent_context = self._get_recent_context()
            
            if recent_context:
                # Add context to prompt
                extras = loop_data.extras_persistent
                
                # Clean up any existing memory entries
                for key in list(extras.keys()):
                    if 'memor' in key.lower() or 'context' in key.lower():
                        del extras[key]
                
                # Add simple context
                context_prompt = f"""## Recent Conversation Context
{recent_context}

Use this context to provide informed responses while staying focused on the current conversation."""
                
                extras["conversation_context"] = context_prompt
                
                log_item.update(
                    heading="✅ Added conversation context",
                    context=recent_context[:200] + "..." if len(recent_context) > 200 else recent_context
                )
            else:
                log_item.update(
                    heading="📝 No additional context needed",
                    temp=True
                )
            
        except Exception as e:
            PrintStyle.error(f"Simple context error: {str(e)}")
            # Log the error but don't fail
            self.agent.context.log.log(
                type="error",
                content=f"Context error: {str(e)}",
                temp=True
            )
    
    def _get_recent_context(self) -> str:
        """Get recent conversation context"""
        try:
            # Get conversation history from agent
            history_text = self.agent.history.output_text()
            
            if not history_text:
                return ""
            
            # Split into lines and get recent messages
            lines = [line.strip() for line in history_text.split('\n') if line.strip()]
            
            # Get last 10 lines of conversation
            recent_lines = lines[-10:] if len(lines) > 10 else lines
            
            # Format as context
            context_lines = []
            for line in recent_lines:
                if line and not line.startswith('System:'):
                    # Clean up the line
                    if ':' in line:
                        speaker, content = line.split(':', 1)
                        content = content.strip()
                        if content and len(content) > 5:  # Only include substantial content
                            context_lines.append(f"{speaker.strip()}: {content}")
            
            # Return recent context
            return '\n'.join(context_lines[-6:])  # Last 6 substantial exchanges
            
        except Exception as e:
            PrintStyle.error(f"Failed to get recent context: {str(e)}")
            return ""
