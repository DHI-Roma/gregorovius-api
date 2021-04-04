[![build](https://github.com/03b8/gregorovius-api/workflows/build/badge.svg)](https://github.com/03b8/gregorovius-api/actions?query=workflow%3Abuild)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Gregorovius API** is the main backend application for the
[Gregorovius Correspondence Edition](https://gregorovius-edition.dhi-roma.it).
It acts as an API layer on top of eXist-db and can be consumed as a web service
by any application. Gregorovius API is based on [FastAPI](https://fastapi.tiangolo.com/),
[delb](https://delb.readthedocs.io/) and [snakesist](https://snakesist.readthedocs.io/)
and implements an API configuration model
[proposed by Martin Fechner in 2018](https://core.ac.uk/download/pdf/154356753.pdf#page=205).

The Gregorovius Correspondence Edition is developed by the German Historical
Institute in Rome in collaboration with the Berlin-Brandenburg Academy of Sciences and
Humanities, with funding from the German Research Foundation and the Gerda Henkel Foundation.

## Customizing and developing the backend app

* Make sure you have [Poetry](https://poetry.eustace.io/docs/) 
  and Python 3.6 installed
* Install dependencies by running `$ poetry install` in the root directory
* Make sure you have an eXist instance running locally on `db:8080`
  (eXist 4.7.1, ideally, or lower). If "db" doesn't cut it, adjust the host
  name as you please in `app/controller.py`
* Start the server `poetry run uvicorn app:main --reload` 
  (reload flag is optional)
* Run the test suite as needed: `$ poetry run pytest`

## Setting up the manifest file

`config.yml` is the manifest file which determines the content
and structure of the data served by the web service.
First, a few things to consider when setting up `config.yml`:

* The file must be valid YAML, of course
* Please stick to a two-space indentation

### Manifest sections

Currently the manifest file is tailored for eXist-db and
uses XPath expressions to determine what data needs to queried.

#### Collection path
You can provide a path to the eXist collection at the root of your project,
to limit the spectrum of queries to that collection, e. g.

```yaml
collection: /db/projects/gregorovius/data
```

#### XSLT option
If you want to allow XSLT (1.0) transformations for your XML endpoints,
you can set the XSLT option to `True`. XSLT is disabled by default.

```yaml
xslt: True
```

When using the XSLT transformation feature, please note that
the stylesheets processed by the app are restricted for security reasons: The
body of an XSLT request must contain a stylesheet stripped of its root node.

#### Entity definition

Under the `entities:` block you define the items which will become
your API endpoints. For instance, let's say we need two endpoints, letters and persons:

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

Notice how the root XPath differs from the deeper one in properties.
First of all, the root XPath is a string, while the other ones are arrays.
Root XPath expressions also must have namespace prefixes while the others must not.
For now, a namespace prefix wildcard (`*:`) should do the trick. 
Certain predefined prefixes (`tei:`, `xml:` etc.) should be made 
available in a future version.

If you want to specify namespaces in tag names or attribute keys in your `config.yml`,
use the full XML namespace URI. For example, if you want to specifically get the value of `xml:id`,
you can do it like this:

```yml
properties:
  comments:
  xpath: ['.//seg/note']
  attrib: ['{http://www.w3.org/XML/1998/namespace}id']
  multiple: True
```

      

#### Properties in entity definitions

Properties, like the ones seen in the example above, can be nested.
Each of them can have an `xpath: ` line pointing to the property value
by using an *array* of XPath expressions.
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

#### Fulltext search index configuration

*Note: Please refer to the [eXist-db Full Text Index documentation](https://exist-db.org/exist/apps/doc/lucene)*

A basic fulltext search API endpoint can be configured using the `search_index`  
key to set up `text` parameters for the Lucene configuration. The following 
configuration block

```yaml
  search_index:
    text:
    - pattern: "tei:text"
        type: "qname"
        inline-qname: "tei:ex"
        ignore: "tei:note"
    - pattern: "//tei:p"
        type: "match"
        inline-qname: "tei:ex"
        ignore: "tei:note"
```
 
will create the following Lucene configuration in the eXist-db:

```xml
 <analyzer class="org.apache.lucene.analysis.standard.StandardAnalyzer"/>
 <text qname="tei:text">
     <inline qname="tei:ex"/>
     <ignore qname="tei:note" />
 </text>
 <text match="//tei:p">
     <inline qname="tei:ex"/>
     <ignore qname="tei:note"/>
 </text>
```

Notice that the current implementation contains defaults and hard coded values. 
This is an experimental feature for now. Please use with care.
