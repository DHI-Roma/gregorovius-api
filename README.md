This is a Python app for building an API layer between eXist-db and
the frontend applications of  digital scholarly edition. 
It can also be offered as a web service to make your edition
machine readable. The API provides automatic Swagger documentation thanks
to FastAPI.

## Basic usage

* Make sure you have [Poetry](https://poetry.eustace.io/docs/) 
  and Python 3.6 installed
* Install dependencies by running `$ poetry install` in the root directory
* Set up a `config.yml` file in the root directory
* Make sure you have an eXist instance running locally on `localhost:8080`
  (eXist 4.7.1, ideally, or lower).
* Start the server `poetry run uvicorn app:main --reload` 
  (reload flag is optional)

## Setting up the manifest file

First, a few things to consider when setting up `config.yml`:

* The file must be valid YAML, of course
* Please stick to a two-space indentation

### Manifest sections

#### Collection path
You can provide a path to the eXist collection of your project, to
limit the spectrum of queries to that collection, e. g.

```yaml
collection: /db/projects/gregorovius/data
```

#### XSLT option
If you need an XSLT transformation method for your XML endpoints, 
you can switch the XSLT option to `True`. XSLT is disabled by default.

```yaml
xslt: True
```

#### Entity definition

Under an `entities:` block you define the items which will become
your API endpoints. For instance, let's say we need letters and persons:

```yaml
entities:
  letters:
    xpath: '//*:TEI[@*:doctype="letter"]'
  persons:
    xpath: '//*:TEI[@*:doctype="person_index"]//*:person'
    properties:
      name:
        xpath:
          - './persName[@type="reg"]'
```

Notice how the root XPath differs from the deeper one in properties. The
root XPath must have namespace prefixes while the others must not. 
For now, a namespace prefix wildcard (`*:`) should do the trick. 
Certain predefined prefixes (`tei:`, `xml:` etc.) should be made 
available in a future version.

#### Properties in entity definitions

Properties can be nested. They can have an `xpath: ` value. 
If they don't, any deeper XPath will be resolved relative to the 
entity root. By default, properties yield a *single value* for a certain
property. 

If you want **multiple values** as an array, you need to set the
`multiple: True` option.

```yaml
properties:
  name:
    xpath:
      - './persName[@type="reg"]'
      - './persName[@type="alt"]'
    multiple: True
```

An XPath yields the text content of the children nodes. If you want to 
extract an attribute value, insert an `attr` option:

```yaml
  persons:
    xpath: '//*:TEI[@*:doctype="person_index"]//*:person'
    properties:
      name:
        xpath:
          - './persName[@type="reg"]'
        attr: ['key']
```

The property ID extracted by default is the `@xml:id` of your entity node.
Other fallback attributes for the ID are not available atm, but planned 
for a future version.