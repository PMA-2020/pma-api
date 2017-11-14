# PMA API
This is the PMA2020 API.

# Developer Documentation
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
- Back-slash, `\ `: For character escaping (TODO).
- Question mark, `?`: For specifying query parameters.
- Ampersand, `&`: Query parameter delimiter.
- Equals-sign, `=`: Keyword query parameter assignment operator.
- Comma, `,`: List item delimiter.

#### Character Escpaing
TODO

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

### Querying Collections and Entities
TODO

### Query Parameters
#### Filtering
TODO

#### Fields
TODO

#### Format
TODO


## Common Endpoints

### Root `/v1/`
This endpoint re-routes directly to: `/v1/resources`

### Resources `/v1/resources`
Returns a list of core resources. Takes no arguments.

Example: `/v1/resources`
```
{
  "resources": [
    {
      "name": "countries",
      "resource": "https://<base_url>/surveys"
    },
    {
      "name": "surveys",
      "resource": "https://<base_url>/surveys"
    },
    {
      "name": "texts",
      "resource": "https://<base_url>/texts"
    },
    {
      "name": "indicators",
      "resource": "https://<base_url>/indicators"
    },
    {
      "name": "data",
      "resource": "https://<base_url>/data"
    },
    {
      "name": "characteristicGroups",
      "resource": "https://<base_url>/characteristicGroups"
    }
  ]
}
```

### Version `/v1/version`
Returns API 2-part semantic version number of form "#.#". Takes no arguments.

Example: `/v1/version`
```
{
    "version": "0.1"
}
```

## Application Specific Endpoints
This is documentation for application specific endpoints, such as
[PMA2020 Datalab](http://datalab.pma2020.org).

### Application initialization `/v1/datalab/init`
Returns lists of all specific, key resources (surveys, indicators, and
characteristics), all of which have at least one stored data point associated.
Takes no arguments.

Example: `/v1/datalab/init`
```
{
  "characteristicGroups": [
    {
      "category.id": "To be implemented.",
      "definition.id": "0UI5Qdrh",
      "id": "wealth_quintile",
      "label.id": "BP8WlFPW",
      "order": "To be implemented."
    },
    ...
  ],
  "characteristics": [
    {
      "id": "none",
      "label.id": "jVwfpK1a",
      "order": 0
    },
    ...
  ],
  "indicators": [
    {
      "category.id": "h2koO9c-",
      "definition.id": "e3E-GqDL",
      "id": "uneed_tot_aw",
      "label.id": "e3E-GqDL",
      "order": 80
    },
    ...
  ],
  "languages": {
    "en": "English",
    "fr": "French",
    ...
  },
  "strings": {
    "-iTSAPqU": {
      "en": "Non-user"
    },
    "-lfInUMt": {
      "en": "Highest"
    },
    ...
  },
  "surveys": [
    {
      "country.label.id": 3,
      "geography.label.id": "To be implemented.",
      "id": "KE2014PMA",
      "label.id": "To be implemented.",
      "order": 601
    },
    ...
  ]
}
```

### Query for valid combinations of key resources `/v1/datalab/combos`
Query for valid combinations of key resources, given any combination of 3 possible key
resources required for rendering visualizations. A valid combinations of
resources is defined as resources that, when passed to `v1/data` or
`v1/datalab/data`, will return 1 or more data points. This endpoint requires
1-3 of the following parameters (key resources): "survey", "indicator", or
"characteristicGroup".

#### A. Query by survey `/v1/datalab/combos?survey=<surveys>`
A list of indicator and characteristic combinations which have one or more
stored data point associated with any of the provided surveys. From this list
provided, the client application should have enough information to filter valid
data isaggregated further by specified indicator(s) and characteristic(s),
without the need for any further API calls.

Example: `/v1/datalab/combos?survey=GH2013PMA,GH2014PMA`
```
{
  "characteristicGroup.id": [
    "none",
    "residence",
    "wealth_quintile"
  ],
  "indicator.id": [
    "mcpr_aw",
    "uneed_tot_aw"
  ],
  "survey.id": [
    "GH2013PMA",
    "GH2014PMA",
    "GH2015PMA",
    "KE2014PMA",
    "KE2015PMA",
    "KE2015PMA_2"
  ]
}
```

#### B. Query by indicator or characteristicGroup `/v1/datalab?[indicator | characteristicGroup]=<id>`
Filtering by either indicator or characteristicGroup returns a list of
indicators or characteristics (whichever was not provided in the query) which
have one or more stored data point associated, and a separate list of surveys
which have one or more stored data point associated.

Example: `/v1/datalab/combos?indicator=mcpr_aw`
```
{
  "characteristicGroup.id": [
    "none",
    "residence",
    "wealth_quintile"
  ],
  "indicator.id": [
    "mcpr_aw",
    "uneed_tot_aw"
  ],
  "survey.id": [
    "GH2013PMA",
    "GH2014PMA",
    "GH2015PMA",
    "KE2014PMA",
    "KE2015PMA",
    "KE2015PMA_2"
  ]
}
```

Example: `/v1/datalab/combos?characteristicGroup=wealth_quintile`
```
{
  "characteristicGroup.id": [
    "none",
    "residence",
    "wealth_quintile"
  ],
  "indicator.id": [
    "mcpr_aw",
    "uneed_tot_aw"
  ],
  "survey.id": [
    "GH2013PMA",
    "GH2014PMA",
    "GH2015PMA",
    "KE2014PMA",
    "KE2015PMA",
    "KE2015PMA_2"
  ]
}
```

#### C. Query by 2 of 3 key resources `/v1/datalab/combos?<resource_1>=<id>&<resource_2>=<id>`
Filter by 2 of 3 of the `/datalab/combos` parameters: "survey", "indicator", and
"characteristicGroup".

Example: `/v1/datalab/combos?survey=GH2015PMA&indicator=mcpr_aw`
```
{
  "characteristicGroup.id": [
    "none",
    "residence",
    "wealth_quintile"
  ],
  "indicator.id": [
    "mcpr_aw",
    "uneed_tot_aw"
  ],
  "survey.id": [
    "GH2013PMA",
    "GH2014PMA",
    "GH2015PMA",
    "KE2014PMA",
    "KE2015PMA",
    "KE2015PMA_2"
  ]
}
```

### Querying application-specific data `/v1/datalab/data`
Returns list of data points with minimal number of fields necessary for
rendering visualizations.

#### Required Parameters
- `survey` *(string)* - Survey.
- `indicator` *(string)* - Indicator.
- `characteristicGroup` *(string)* - Characteristic group.

Example: `/v1/datalab/data?survey=GH2013PMA,GH2014PMA&indicator=mcpr_aw&characteristicGroup=none`
```
{
  "chartOptions": {
    "precision": 1
  },
  "metadata": {
    "datasetMetadata": [
      {
        "createdOn": "Thu, 14 Sep 2017 20:32:02 GMT",
        "hash": "ef5c8634e0dbc812a3df9b0882873db9",
        "name": "api_data",
        "type": "api"
      },
      {
        "createdOn": "Thu, 14 Sep 2017 20:32:02 GMT",
        "hash": "cca82c783607b2bf1431ac5bcd26f8cc",
        "name": "ui_data",
        "type": "ui"
      }
    ],
    "version": "0.1.8"
  },
  "queryInput": {
    "characteristicGroups": [
      {
        "definition.id": "PRE_iU_n",
        "id": "none",
        "label.id": "XkVmGDDF"
      }
    ],
    "indicators": [
      {
        "definition.id": "NQv8ZZOp",
        "id": "mcpr_aw",
        "label.id": "NQv8ZZOp"
      }
    ],
    "surveys": [
      {
        "country.label.id": "6EA0At85",
        "geography.label.id": "w748V1ul",
        "id": "GH2013PMA",
        "label.id": "lq0db_sX",
        "partner.label.id": "cizmJ6Gv"
      },
      {
        "country.label.id": "6EA0At85",
        "geography.label.id": "w748V1ul",
        "id": "GH2014PMA",
        "label.id": "2Ea5SlF4",
        "partner.label.id": "cizmJ6Gv"
      }
    ]
  },
  "resultSize": 2,
  "results": [
    {
      "country.id": "GH",
      "country.label.id": "6EA0At85",
      "geography.id": "gh_national",
      "geography.label.id": "w748V1ul",
      "survey.id": "GH2013PMA",
      "survey.label.id": "lq0db_sX",
      "values": [
        {
          "characteristic.id": "none",
          "characteristic.label.id": "J-N_aTkS",
          "value": 15.4
        }
      ]
    },
    {
      "country.id": "GH",
      "country.label.id": "6EA0At85",
      "geography.id": "gh_national",
      "geography.label.id": "w748V1ul",
      "survey.id": "GH2014PMA",
      "survey.label.id": "2Ea5SlF4",
      "values": [
        {
          "characteristic.id": "none",
          "characteristic.label.id": "J-N_aTkS",
          "value": 16.1
        }
      ]
    }
  ]
}
```

#### Optional Parameters
##### Querying Time Series Data
- `overTime` *(boolean)*

Supplying this query parameter and setting value to `true` will tell the API
to return chronologically sorted data, and also include a `date` attribute for
 each data point. If not supplied, the API will automatically interpret this
 value as `false`.

Example: `/v1/datalab/data?survey=GH2013PMA,GH2014PMA&indicator=mcpr_aw&characteristicGroup=none&overTime=true`
```
{
  "chartOptions": {
    "precision": 1
  },
  "metadata": {
    "datasetMetadata": [
      {
        "createdOn": "Thu, 14 Sep 2017 20:32:02 GMT",
        "hash": "ef5c8634e0dbc812a3df9b0882873db9",
        "name": "api_data",
        "type": "api"
      },
      {
        "createdOn": "Thu, 14 Sep 2017 20:32:02 GMT",
        "hash": "cca82c783607b2bf1431ac5bcd26f8cc",
        "name": "ui_data",
        "type": "ui"
      }
    ],
    "version": "0.1.8"
  },
  "queryInput": {
    "characteristicGroups": [
      {
        "definition.id": "PRE_iU_n",
        "id": "none",
        "label.id": "XkVmGDDF"
      }
    ],
    "indicators": [
      {
        "definition.id": "NQv8ZZOp",
        "id": "mcpr_aw",
        "label.id": "NQv8ZZOp"
      }
    ],
    "surveys": [
      {
        "country.label.id": "6EA0At85",
        "geography.label.id": "w748V1ul",
        "id": "GH2013PMA",
        "label.id": "lq0db_sX",
        "partner.label.id": "cizmJ6Gv"
      },
      {
        "country.label.id": "6EA0At85",
        "geography.label.id": "w748V1ul",
        "id": "GH2014PMA",
        "label.id": "2Ea5SlF4",
        "partner.label.id": "cizmJ6Gv"
      }
    ]
  },
  "resultSize": 1,
  "results": [
    {
      "characteristic.id": "none",
      "characteristic.label.id": "J-N_aTkS",
      "country.id": "GH",
      "country.label.id": "6EA0At85",
      "geography.id": "gh_national",
      "geography.label.id": "w748V1ul",
      "values": [
        {
          "survey.date": "2013-10-03",
          "survey.id": "GH2013PMA",
          "survey.label.id": "lq0db_sX",
          "value": 15.4
        },
        {
          "survey.date": "2014-01-01",
          "survey.id": "GH2014PMA",
          "survey.label.id": "2Ea5SlF4",
          "value": 16.1
        }
      ]
    }
  ]
}
```
##### CSV download
- `format=csv`
Add `format=csv` to the query parameters to get a csv download.
- `lang=LC`
Add `lang=LC` where `LC` is the language code (e.g. `en` or `fr`) for the data download. This is optional, and the default is English.
