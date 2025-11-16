"""
Tool executor for agent-driven design document modifications.

Executes tool invocations by applying edits to the design document markdown.
"""

import re
from typing import List, Optional
from app.agent.doc_tools import (
    DesignDocToolInvocation,
    UpdateSectionTool,
    ReplaceSectionTool,
    AppendSectionTool,
    DeleteSectionTool,
    AddSectionTool,
)
from app.session.manager import session_manager


class DocToolExecutionError(Exception):
    """Raised when a design doc tool execution fails."""
    pass


class DesignDocToolExecutor:
    """
    Executes design document editing tools returned by the AI agent.

    This class provides markdown manipulation operations for the design document.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session = session_manager.get_session(session_id)
        if not self.session:
            raise DocToolExecutionError(f"Session {session_id} not found")

        # Get current design doc
        self.design_doc = self.session.design_doc or ""

    def execute_tools(self, tool_invocation: DesignDocToolInvocation) -> str:
        """
        Execute all design doc tools in the invocation sequentially.

        Args:
            tool_invocation: DesignDocToolInvocation object with list of tools

        Returns:
            Updated design document markdown

        Raises:
            DocToolExecutionError: If any tool execution fails
        """
        results = []

        for i, tool in enumerate(tool_invocation.doc_tools):
            try:
                print(f"\n=== Executing Design Doc Tool {i+1}/{len(tool_invocation.doc_tools)} ===")
                print(f"Action: {tool.action}")

                if tool.action == "update_section":
                    self._execute_update_section(tool)
                elif tool.action == "replace_section":
                    self._execute_replace_section(tool)
                elif tool.action == "append_section":
                    self._execute_append_section(tool)
                elif tool.action == "delete_section":
                    self._execute_delete_section(tool)
                elif tool.action == "add_section":
                    self._execute_add_section(tool)
                else:
                    raise DocToolExecutionError(f"Unknown action: {tool.action}")

                results.append(True)
                print(f"✓ Design doc tool executed successfully")

            except Exception as e:
                error_msg = f"Failed to execute design doc tool {i+1} ({tool.action}): {str(e)}"
                print(f"✗ {error_msg}")
                raise DocToolExecutionError(error_msg) from e

        print(f"\n=== All {len(tool_invocation.doc_tools)} design doc tools executed successfully ===")

        # Persist updated design doc to session
        session_manager.update_design_doc(self.session_id, self.design_doc)

        return self.design_doc

    def _find_section(self, section_header: str) -> Optional[tuple]:
        """
        Find a section in the markdown by header.

        Returns:
            (start_index, end_index, header_line, content) or None if not found
        """
        lines = self.design_doc.split('\n')

        # Find the section header line
        header_index = None
        for i, line in enumerate(lines):
            if line.strip() == section_header.strip():
                header_index = i
                break

        if header_index is None:
            return None

        # Determine the section level (number of # symbols)
        header_level = len(re.match(r'^(#+)', section_header).group(1))

        # Find the end of this section (next same-or-higher-level header)
        end_index = len(lines)  # Default to end of document
        for i in range(header_index + 1, len(lines)):
            line = lines[i]
            header_match = re.match(r'^(#+)\s+', line)
            if header_match:
                current_level = len(header_match.group(1))
                if current_level <= header_level:
                    end_index = i
                    break

        # Extract content (everything between header and next section)
        content_lines = lines[header_index + 1:end_index]
        content = '\n'.join(content_lines)

        return (header_index, end_index, lines[header_index], content)

    def _execute_update_section(self, tool: UpdateSectionTool) -> None:
        """Execute update_section tool - find and replace within a section."""
        section_info = self._find_section(tool.section_header)

        if not section_info:
            raise DocToolExecutionError(
                f"Section not found: '{tool.section_header}'. "
                f"Make sure the header matches exactly (including # symbols)."
            )

        header_index, end_index, header_line, content = section_info

        # Special case: If find_text matches the section header, update the header itself
        if tool.find_text.strip() == header_line.strip():
            # Update the header line
            lines = self.design_doc.split('\n')
            lines[header_index] = tool.replace_text
            self.design_doc = '\n'.join(lines)
            print(f"  Updated section header: '{tool.find_text}' → '{tool.replace_text}'")
            return

        # Perform find-and-replace within this section's content
        if tool.find_text not in content:
            raise DocToolExecutionError(
                f"Text not found in section '{tool.section_header}': '{tool.find_text}'. "
                f"The find text must match exactly (character-for-character). "
                f"Consider using replace_section if you're not sure about exact formatting."
            )

        # Replace the text
        updated_content = content.replace(tool.find_text, tool.replace_text, 1)  # Replace first occurrence

        # Rebuild the document
        lines = self.design_doc.split('\n')
        new_lines = (
            lines[:header_index + 1] +  # Everything before and including header
            updated_content.split('\n') +  # Updated section content
            lines[end_index:]  # Everything after this section
        )
        self.design_doc = '\n'.join(new_lines)

        print(f"  Updated section: {tool.section_header}")
        print(f"  Replaced: '{tool.find_text[:50]}...' → '{tool.replace_text[:50]}...'")

    def _execute_replace_section(self, tool: ReplaceSectionTool) -> None:
        """Execute replace_section tool - replace entire section content."""
        section_info = self._find_section(tool.section_header)

        if not section_info:
            raise DocToolExecutionError(
                f"Section not found: '{tool.section_header}'. "
                f"Make sure the header matches exactly (including # symbols)."
            )

        header_index, end_index, header_line, content = section_info

        # Rebuild the document with new content
        lines = self.design_doc.split('\n')
        new_lines = (
            lines[:header_index + 1] +  # Everything before and including header
            tool.new_content.split('\n') +  # New section content
            lines[end_index:]  # Everything after this section
        )
        self.design_doc = '\n'.join(new_lines)

        print(f"  Replaced section: {tool.section_header}")
        print(f"  Old content length: {len(content)} chars, New: {len(tool.new_content)} chars")

    def _execute_append_section(self, tool: AppendSectionTool) -> None:
        """Execute append_section tool - add content to end of section."""
        section_info = self._find_section(tool.section_header)

        if not section_info:
            raise DocToolExecutionError(
                f"Section not found: '{tool.section_header}'. "
                f"Make sure the header matches exactly (including # symbols)."
            )

        header_index, end_index, header_line, content = section_info

        # Append new content to existing content
        updated_content = content + tool.content

        # Rebuild the document
        lines = self.design_doc.split('\n')
        new_lines = (
            lines[:header_index + 1] +  # Everything before and including header
            updated_content.split('\n') +  # Existing content + appended content
            lines[end_index:]  # Everything after this section
        )
        self.design_doc = '\n'.join(new_lines)

        print(f"  Appended to section: {tool.section_header}")
        print(f"  Added {len(tool.content)} chars")

    def _execute_delete_section(self, tool: DeleteSectionTool) -> None:
        """Execute delete_section tool - remove entire section including header."""
        section_info = self._find_section(tool.section_header)

        if not section_info:
            # Section not found - skip gracefully (might already be deleted)
            print(f"  ⚠️  Section '{tool.section_header}' not found (already deleted or never existed)")
            return

        header_index, end_index, header_line, content = section_info

        # Rebuild the document without this section
        lines = self.design_doc.split('\n')
        new_lines = (
            lines[:header_index] +  # Everything before header
            lines[end_index:]  # Everything after this section
        )
        self.design_doc = '\n'.join(new_lines)

        print(f"  Deleted section: {tool.section_header}")
        print(f"  Removed {end_index - header_index} lines")

    def _execute_add_section(self, tool: AddSectionTool) -> None:
        """Execute add_section tool - insert new section at specified location."""
        if tool.insert_after:
            # Find the section to insert after
            section_info = self._find_section(tool.insert_after)

            if not section_info:
                raise DocToolExecutionError(
                    f"Insert location not found: '{tool.insert_after}'. "
                    f"Make sure the header matches exactly (including # symbols)."
                )

            header_index, end_index, header_line, content = section_info
            insert_index = end_index  # Insert right after this section
        else:
            # Insert at end of document
            lines = self.design_doc.split('\n')
            insert_index = len(lines)

        # Build the new section
        new_section_lines = [
            tool.section_header,  # Header
            *tool.content.split('\n')  # Content
        ]

        # Rebuild the document with new section inserted
        lines = self.design_doc.split('\n')
        new_lines = (
            lines[:insert_index] +  # Everything before insertion point
            new_section_lines +  # New section
            lines[insert_index:]  # Everything after insertion point
        )
        self.design_doc = '\n'.join(new_lines)

        insert_location = tool.insert_after if tool.insert_after else "end of document"
        print(f"  Added section: {tool.section_header}")
        print(f"  Inserted after: {insert_location}")


def execute_doc_tool_invocation(session_id: str, tool_invocation: DesignDocToolInvocation) -> str:
    """
    Convenience function to execute a design doc tool invocation.

    Args:
        session_id: Session ID
        tool_invocation: DesignDocToolInvocation object

    Returns:
        Updated design document markdown

    Raises:
        DocToolExecutionError: If execution fails
    """
    executor = DesignDocToolExecutor(session_id)
    return executor.execute_tools(tool_invocation)
