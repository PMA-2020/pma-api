# Using the API
## Navigation
### Resource Lists
Resource roots are endpoints that return a list of resources and URLs to those
resources. The resource list for common endpoints can be found at `/v#` or
`/v#/resources`, and the resource list for application-specific endpoints can
be found at `/v#/datalab` or `v#/datalab/resources`, where "#" is the API
version number.

### Navigating API Versions
Leaving `/v#/` out of your API query URLs will default to the most recent,
stable API verison. To prevent unexpected results, it is advised to always
supply a version number.

## Syntax
### The Query String
#### Special Character Meanings
- Forward-slash, `/`: Only for URL pathing.
- Back-slash, `\ `: For character escaping (Available in [upcoming release](https://github.com/PMA-2020/pma-api/releases/tag/2.0.0).)
- Question mark, `?`: For specifying query parameters.
- Ampersand, `&`: Query parameter delimiter.
- Equals-sign, `=`: Keyword query parameter assignment operator.
- Comma, `,`: List item delimiter.

#### Character Escaping
Available in [upcoming release](https://github.com/PMA-2020/pma-api/releases/tag/2.0.0).

### Data Types
#### Primitives
In an API query URL string, specific data types should be used as follows and
should be specified witout quotation marks (`"` or `'`).
##### String
Example: `/v1/datalab/data?survey=GH2013PMA`.

##### Integer
Example: `/v1/datalab/data?precision=1`.

##### Float
Example: `/v1/datalab/data?value=15.4`.

##### Boolean
Booleans can be any upper or lower case variant of 'true' or 'false'. Values
"1", "0", "null", "none" are examples of non-booleans.
Example: `/v1/datalab/indicator?isFavorite=true`.

##### Null
Null can be any upper or lower case variant of 'null'.  Values "0" and "none"
are examples of non-null values.
Example: `/v1/datalab/indicator?isFavorite=null`.

##### None
None can be any upper or lower case variant of 'none'.  Values "0" and "null"
are examples of non-none values.
Example: `/v1/data?char1.id=none`

#### Lists
Lists are simply comma separated strings without qotation marks (`"` or `'`).
Example: `/v1/datalab/combos?survey=GH2013PMA,GH2014PMA`

### Query Parameters
#### Filtering
Available in [upcoming release](https://github.com/PMA-2020/pma-api/releases/tag/2.0.0).

#### Fields
Available in [upcoming release](https://github.com/PMA-2020/pma-api/releases/tag/2.0.0).

#### Format
Available in [upcoming release](https://github.com/PMA-2020/pma-api/releases/tag/2.0.0).
