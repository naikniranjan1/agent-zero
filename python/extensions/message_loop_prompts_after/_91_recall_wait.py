from python.helpers.extension import Extension
from agent import LoopData


class RecallWait(Extension):
    """
    Smart Recall Wait Extension
    Updated to work with the new smart hybrid memory system
    """

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        """
        Wait for smart memory processing to complete
        This extension is now simplified since smart recall is much faster
        """

        # Check if there's a smart recall task running
        smart_task = self.agent.get_data("_smart_recall_task")
        if smart_task and not smart_task.done():
            # Wait for smart recall to complete (should be very fast)
            await smart_task

        # The smart system is so fast that we rarely need to wait
        # Most queries complete in < 200ms

