from service.helpers import process_properties
from delb import Document


def test_process_properties_single():
    """
    Test extraction of two properties
    with nodes located at different depths
    with single values
    """
    manifest = {
        "spam": {
            "xpath": [".//spam"],
            "properties": {
                "foo": {
                    "xpath": ["."],
                },
            },
        }
    }
    node = Document(
        "<foo>"
        "<spam>def</spam>"
        "</foo>"
    ).root
    properties = {
        "spam": {
            "foo": "def"
        }
    }
    assert process_properties(manifest, node) == properties


def test_process_properties_xpath_current():
    """
    Test extraction of a property
    selecting current node
    with XPath expression '.'
    """
    manifest = {
        "spam": {
            "xpath": [".//spam"]
        },
        "ham": {
            "xpath": [".//ham"]
        }
    }
    node = Document(
        "<foo>"
        "<bar><ham>abc</ham></bar>"
        "<spam>def</spam>"
        "</foo>"
    ).root
    properties = {
        "ham": "abc",
        "spam": "def"
    }
    assert process_properties(manifest, node) == properties

def test_process_properties_single_attrib():
    """
    Test extraction of two properties
    with nodes located at different depths
    with single values from attributes
    """
    manifest = {
        "spam": {
            "xpath": [".//spam"],
            "attrib": ["id"]
        },
        "ham": {
            "xpath": [".//ham"],
            "attrib": ["id"]
        }
    }
    node = Document(
        "<foo>"
        "<bar><ham id='x'>abc</ham></bar>"
        "<spam id='y'>def</spam>"
        "</foo>"
    ).root
    properties = {
        "ham": "x",
        "spam": "y"
    }
    assert process_properties(manifest, node) == properties


def test_process_properties_multiple():
    """
    Test extraction of a property
    with nodes located at different depths
    with multiple values
    """
    manifest = {
        "spam": {
            "xpath": [".//spam"],
            "multiple": True
        }
    }
    node = Document(
        "<foo>"
        "<bar><spam>abc</spam></bar>"
        "<spam>def</spam>"
        "</foo>"
    ).root
    properties = {
        "spam": ["abc", "def"]
    }
    assert process_properties(manifest, node) == properties


def test_process_properties_multiple_nested_root():
    """
    Test extraction of a nested property
    with nodes located at different depths
    with multiple values
    relative to root
    """
    manifest = {
        "spam": {
            "properties": {
                "ham": {
                    "xpath": [".//ham"],
                    "multiple": True
                }
            }
        }
    }
    node = Document(
        "<foo>"
        "<ham>xyz</ham>"
        "<spam>"
        "<bar><ham>abc</ham><ham>def</ham></bar>"
        "</spam>"
        "</foo>"
    ).root
    properties = {
        "spam": {"ham": ["xyz", "abc", "def"]}
    }
    assert process_properties(manifest, node) == properties


def test_process_properties_multiple_nested_xpath():
    """
    Test extraction of a nested property
    with nodes located at different depths
    with multiple values
    relative to parent property xpath
    """
    manifest = {
        "spam": {
            "xpath": [".//spam"],
            "properties": {
                "ham": {
                    "xpath": [".//ham"],
                    "multiple": True
                }
            }
        }
    }
    node = Document(
        "<foo>"
        "<ham>xyz</ham>"
        "<spam>"
        "<bar><ham>abc</ham><ham>def</ham></bar>"
        "</spam>"
        "</foo>"
    ).root
    properties = {
        "spam": {"ham": ["abc", "def"]}
    }
    assert process_properties(manifest, node) == properties


def test_process_properties_multiple_nested_prop_objects():
    """
    Test extraction of a nested property
    with nodes located at different depths
    with multiple property value objects
    relative to parent property xpath
    """
    manifest = {
        "foo": {
            "xpath": [".//foo"],
            "multiple": True,
            "properties": {
                "ham": {
                    "xpath": ["./ham"],
                },
                "spam": {
                    "xpath": ["./spam"],
                }
            }
        }
    }
    node = Document(
        "<root>"
        "<foo>"
        "<ham>abc</ham>"
        "<spam>def</spam>"
        "</foo>"
        "<foo>"
        "<ham>uvw</ham>"
        "<spam>xyz</spam>"
        "</foo>"
        "</root>"
    ).root
    properties = {
        "foo": [
            {
                "ham": "abc",
                "spam": "def"
            },
            {
                "ham": "uvw",
                "spam": "xyz"
            }
        ]
    }
    assert process_properties(manifest, node) == properties

