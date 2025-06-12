import os
from dataclasses import dataclass
from python.helpers.tool import Tool, Response
from python.helpers import files
from python.helpers.print_style import PrintStyle
import PyPDF2
import pypdf


class PDFProcessing(Tool):
    """
    Tool for processing PDF files locally using PyPDF2/pypdf without requiring Docker or RFC.
    Supports text extraction, page counting, and basic PDF operations.
    """

    async def execute(self, **kwargs):
        await self.agent.handle_intervention()

        action = self.args.get("action", "extract_text").lower().strip()
        file_path = self.args.get("file_path", "").strip()
        
        if not file_path:
            return Response(
                message="Error: file_path parameter is required.",
                break_loop=False
            )

        # Convert relative path to absolute path
        if not os.path.isabs(file_path):
            file_path = files.get_abs_path(file_path)

        if not os.path.exists(file_path):
            return Response(
                message=f"Error: File not found at {file_path}",
                break_loop=False
            )

        if not file_path.lower().endswith('.pdf'):
            return Response(
                message="Error: File must be a PDF (.pdf extension required).",
                break_loop=False
            )

        try:
            if action == "extract_text":
                result = await self.extract_text_from_pdf(file_path)
            elif action == "get_info":
                result = await self.get_pdf_info(file_path)
            elif action == "extract_page":
                page_num = int(self.args.get("page_number", 1))
                result = await self.extract_page_text(file_path, page_num)
            else:
                result = f"Error: Unknown action '{action}'. Supported actions: extract_text, get_info, extract_page"

            return Response(message=result, break_loop=False)

        except Exception as e:
            error_msg = f"Error processing PDF: {str(e)}"
            PrintStyle.error(error_msg)
            return Response(message=error_msg, break_loop=False)

    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract all text from PDF using PyPDF2"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                full_text = ""
                total_pages = len(reader.pages)
                
                for page_num, page in enumerate(reader.pages, start=1):
                    full_text += f"--- Page {page_num} of {total_pages} ---\n"
                    text = page.extract_text()
                    full_text += (text or '') + "\n\n"
                
                if not full_text.strip():
                    return "Warning: No text could be extracted from the PDF. The PDF might contain only images or be encrypted."
                
                return full_text.strip()
                
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    async def get_pdf_info(self, file_path: str) -> str:
        """Get basic information about the PDF"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                info = []
                info.append(f"File: {os.path.basename(file_path)}")
                info.append(f"Total Pages: {len(reader.pages)}")
                
                # Try to get metadata
                if reader.metadata:
                    metadata = reader.metadata
                    if metadata.title:
                        info.append(f"Title: {metadata.title}")
                    if metadata.author:
                        info.append(f"Author: {metadata.author}")
                    if metadata.subject:
                        info.append(f"Subject: {metadata.subject}")
                    if metadata.creator:
                        info.append(f"Creator: {metadata.creator}")
                    if metadata.producer:
                        info.append(f"Producer: {metadata.producer}")
                
                # Check if encrypted
                if reader.is_encrypted:
                    info.append("Status: Encrypted (may require password)")
                else:
                    info.append("Status: Not encrypted")
                
                return "\n".join(info)
                
        except Exception as e:
            raise Exception(f"Failed to get PDF info: {str(e)}")

    async def extract_page_text(self, file_path: str, page_number: int) -> str:
        """Extract text from a specific page"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                total_pages = len(reader.pages)
                
                if page_number < 1 or page_number > total_pages:
                    return f"Error: Page number {page_number} is out of range. PDF has {total_pages} pages."
                
                page = reader.pages[page_number - 1]  # Convert to 0-based index
                text = page.extract_text()
                
                if not text.strip():
                    return f"Warning: No text found on page {page_number}. The page might contain only images."
                
                return f"--- Page {page_number} of {total_pages} ---\n{text}"
                
        except Exception as e:
            raise Exception(f"Failed to extract text from page {page_number}: {str(e)}")

    def get_log_object(self):
        return self.agent.context.log.log(
            type="pdf_processing",
            heading=f"{self.agent.agent_name}: Using tool '{self.name}'",
            content="",
            kvps=self.args,
        )

    async def after_execution(self, response, **kwargs):
        self.agent.hist_add_tool_result(self.name, response.message)
