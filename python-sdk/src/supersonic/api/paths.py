"""SuperSonic REST API endpoint path constants.

SuperSonic uses camelCase endpoint names (not RESTful), path changes only need
to update this file. Resource classes and tests share these constants to avoid
hardcoded URLs.
"""


class QueryPaths:
    SQL = "/api/semantic/query/sql"
    SQLS = "/api/semantic/query/sqls"
    VALIDATE = "/api/semantic/query/validate"
    METRIC = "/api/semantic/query/metric"
    CHAT = "/api/semantic/query/chat"


class DomainPaths:
    LIST = "/api/semantic/domain/getDomainList"
    GET = "/api/semantic/domain/getDomain/{id}"
    CREATE = "/api/semantic/domain/createDomain"
    UPDATE = "/api/semantic/domain/updateDomain"
    DELETE = "/api/semantic/domain/deleteDomain/{domain_id}"


class ModelPaths:
    LIST = "/api/semantic/model/getModelList/{domain_id}"
    GET = "/api/semantic/model/getModel/{id}"
    CREATE = "/api/semantic/model/createModel"
    UPDATE = "/api/semantic/model/updateModel"
    DELETE = "/api/semantic/model/deleteModel/{model_id}"


class DimensionPaths:
    LIST = "/api/semantic/dimension/getDimensionList/{model_id}"
    GET = "/api/semantic/dimension/getDimension/{id}"
    CREATE = "/api/semantic/dimension/createDimension"
    UPDATE = "/api/semantic/dimension/updateDimension"
    DELETE = "/api/semantic/dimension/deleteDimension/{id}"
    QUERY_VALUES = "/api/semantic/dimension/queryDimValue"


class MetricPaths:
    LIST = "/api/semantic/metric/queryMetric"
    GET = "/api/semantic/metric/getMetric/{id}"
    CREATE = "/api/semantic/metric/createMetric"
    UPDATE = "/api/semantic/metric/updateMetric"
    DELETE = "/api/semantic/metric/deleteMetric/{id}"
    PUBLISH = "/api/semantic/metric/batchPublish"
    UNPUBLISH = "/api/semantic/metric/batchUnPublish"


class DatabasePaths:
    LIST = "/api/semantic/database/getDatabaseList"
    GET = "/api/semantic/database/getDatabase/{id}"
    # Review fix #9: SuperSonic database endpoint is upsert semantics;
    # create and update share the same path. Request body differs (update
    # carries id). SDK layer splits into two methods for type clarity.
    CREATE = "/api/semantic/database/createOrUpdateDatabase"
    UPDATE = "/api/semantic/database/createOrUpdateDatabase"
    DELETE = "/api/semantic/database/{id}"
    TEST_CONNECT = "/api/semantic/database/testConnect"
    GET_TABLES = "/api/semantic/database/getTables"
    GET_COLUMNS = "/api/semantic/database/getColumnsByName"


class DatasetPaths:
    LIST = "/api/semantic/dataSet/getDataSetList"
    GET = "/api/semantic/dataSet/getDataSet/{id}"
