# [PMA API](#intro)
This is the PMA2020 API.

# [Developer Documentation](#developer-documentation)
This is the developer documentation.
## [Common Endpoints](#common-endpoints)
This is documentation for common API endpoints.

### [Root](#intro) `/`
This endpoint re-routes directly to: `/resources` 

### [Resources](#resources) `/resources`
#### Example 1 - No parameters
Query: `/resources`

Returns:  
A list of resources.
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

## [Application Specific Endpoints](#application-specific-endpoints)
This is documentation for application specific endpoints, such as 
[PMA2020 Datalab](http://datalab.pma2020.org).

### [Application initialization](#application-initialization) `/datalab/init`
Fetch data for all key resources in one request. This endpoint takes no 
query parameters.

Query: `/datalab/init`

Returns:  
A list of all specific, key resources (surveys, indicators, and 
characteristics), all of which have at least one stored data point associated.
```
{
    "indicators": [
        {
            "code": "<item>",
            "label_code": "<item>",
            "definition_code": "<item>",
            "order": "<item>",
            "level2_code": "<item>"
        },
        ...
    ],
    "characteristicGroups": [
        {
            "code": "<item>",
            "label_code": "<item>",
            "definition_code": "<item>",
            "order": "<item>",
            "category_code": "<item>"
        },
        ...
    ],	
    "characteristics": [
        {
            "code": "<item>",
            "label_code": "<item>",
            "order": "<item>"
        },
        ...
    ],
    "surveys": [
        {
            "code": "<item>",
            "label_code": "<item>",
            "order": "<item>",
            "country_label_code": "<item>",
            "geography_label_code": "<item>"
        },
        ...
    ],
    "strings": {
        "en": {
            "code": "<string>",
            ...
        },
        "fr": {
            "code": "<string>",
            ...
        },
		...
    }
    "languages": {
        "en": "English",
		"fr": "French"
		...
    }
}
```

### [Filtering by existing relational data](#filtering-by-existing-relational-data) `/datalab`
#### Example 1 - Filter by all key resources
Query: `/datalab`

Returns:  
A list of all specific, key resources (surveys, indicators, and 
characteristics), all of which have at least one stored data point associated.

#### Example 2 - Filter by surveys
Query: `/datalab?survey=<ID1>,<ID2>,<ID3>`

Returns:  
A list of indicator and characteristic combinations which have one or more 
stored data point associated with any of the provided surveys. From this list 
provided, the client application should have enough information to filter valid
data isaggregated further by specified indicator(s) and characteristic(s), 
without the need for any further API calls.
```
{
    "indicatorCharacteristicCombos": [
        {
            "indicator": "<indicator_code>",
            "characteristic": "<characteristic_code>"
        }, ...
    ],
}
```


#### Example 3 - Filter by indicators or characteristics
Query: `/datalab?[indicator | characteristic]=ID1`

Returns:  
A list of indicators or characteristics (whichever was not provided in the 
query) which have one or more stored data point associated, and a separate list
of surveys which have one or more stored data point associated. Note that these
are separate lists which are returned, as opposed to *example 2* where one list
of all valid combinations are returned.

### [Querying Data](#querying-data) `/datalab/data`
Query data. Accepts parameters: 'survey', 'indicator', and 'characteristic'.
#### Example 1 - Query all data needed to render a visualization 
Query: `/datalab/data?survey=ID1,ID2,ID3&indicator=ID4&characteristicGroup1=ID5&characteristicGroup2=ID6`

Returns:  
A list of all data points filtered by parameters provided.
```
[
    {
        'survey.id':'BAC',
        'indicator.id':'DEF',
        'characteristicGroup1.id':'GTI',
        'characteristic1.id':'15-19',
        'characteristicGroup2.id':'',
        'characteristic2.id':'',
        'value': 0.16,
        'precision': 1
    }, 
    ...
]
```
