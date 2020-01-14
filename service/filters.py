"""
Filter functions for processing property values using the manifest file
"""

from delb import TagNode

class Functions:

    def get_substring_100(selected_node: TagNode) -> str:
        """
        Return the first 100 characters of a node's text content.
        """
        node_content = selected_node.full_text
        try:
            return node_content[:100]
        except IndexError:
            return node_content

    def get_node_name(selected_node: TagNode) -> str:
        """Return the tag name of a node"""
        return selected_node.local_name
