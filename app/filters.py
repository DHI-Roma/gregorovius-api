"""
Filter functions for processing property values using the manifest file
"""

class Functions:

    def get_substring_100(prop_value: str) -> str:
        try:
            return prop_value[:100]
        except IndexError:
            return prop_value
