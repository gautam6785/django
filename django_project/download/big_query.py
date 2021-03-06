from oauth2client.client import GoogleCredentials
from googleapiclient import discovery
import logging
import json
import time
import os
from apiclient.http import MediaFileUpload

class BigQuery:
    __service_singleton = None

    @staticmethod
    def getService():
        if not BigQuery.__service_singleton:
            credentials = GoogleCredentials.get_application_default()
            BigQuery.__service_singleton = discovery.build('bigquery', 'v2', credentials=credentials)
        return BigQuery.__service_singleton


    @staticmethod
    def insertCSV(csv_path,table,truncate = False,debug = False):

        logger = logging.getLogger('GooglePlayApiLogger')
        bigquery = BigQuery.getService()
        
        table_name = 'debug_'+table if debug else table

        insert_request = bigquery.jobs().insert(
            projectId='mobbo-dashboard',
            body={
                'configuration': {
                    'load': {
                        'schema': {
                            'fields': json.load(open("bq_tables/%s.json" % table, 'r'))
                        },
                        'destinationTable': {
                            'projectId': 'mobbo-dashboard',
                            'datasetId': 'mobbo_dashboard',
                            'tableId': table_name
                        },
                        'sourceFormat': 'CSV',
                        'writeDisposition': "WRITE_TRUNCATE" if truncate else "WRITE_APPEND"
                    }
                }
            },
            media_body=MediaFileUpload(
                csv_path,
                mimetype='application/octet-stream'))

        job = insert_request.execute()

        logger.info('Uploading to BigQuery table %s csv:%s truncate:%s' % (table_name,csv_path,truncate))

        status_request = bigquery.jobs().get(
            projectId=job['jobReference']['projectId'],
            jobId=job['jobReference']['jobId'])

        # Poll the job until it finishes.
        while True:
            result = status_request.execute(num_retries=2)

            if result['status']['state'] == 'DONE':
                if result['status'].get('errors'):
                    raise RuntimeError('\n'.join(
                        e['message'] for e in result['status']['errors']))
                if os.path.isfile(csv_path):
                    os.remove(csv_path)
                logger.info('Uploaded table %s' % table_name)
                return

            time.sleep(1)
            
    
    @staticmethod
    def insert_itunesCSV(csv_path,table,truncate = False,debug = False):

        logger = logging.getLogger('GooglePlayApiLogger')
        bigquery = BigQuery.getService()
        
        table_name = 'debug_'+table if debug else table

        insert_request = bigquery.jobs().insert(
            projectId='mobbo-dashboard',
            body={
                'configuration': {
                    'load': {
                        'schema': {
                            'fields': [
                                        {'name': 'customer_id', 'type': 'INTEGER', 'mode': 'REQUIRED', 'description': 'Customer ID'},
                                        {'name': 'customer_account_id', 'type': 'INTEGER', 'mode': 'REQUIRED','description': 'Customer Account ID'},
                                        {'name': 'apple_identifier', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Apple Identifier'},
                                        {'name': 'provider', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Provider'},
                                        {'name': 'provider_country', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Provider Country'},
                                        {'name': 'sku', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Sku'},
                                        {'name': 'developer', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Developer'},
                                        {'name': 'title', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Title'},
                                        {'name': 'version', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Version'},
                                        {'name': 'product_type_identifier', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Product Type Identifier'},
                                        {'name': 'units', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Units'},
                                        {'name': 'developer_proceeds', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Developer Proceeds'},
                                        {'name': 'developer_proceeds_usd', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Developer Proceeds USD'},
                                        {'name': 'begin_date', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable date in UTC (format: YYYY-MM-DD hh:mm:ss)'},
                                        {'name': 'end_date', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable date in UTC (format: YYYY-MM-DD hh:mm:ss)'},
                                        {'name': 'customer_currency', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Customer Currency'},
                                        {'name': 'country_code', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Country Code'},
                                        {'name': 'currency_of_proceeds', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Currency Of Proceeds'},
                                        {'name': 'customer_price', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Customer Price'},
                                        {'name': 'promo_code', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Promo Code'},
                                        {'name': 'parent_identifier', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Parent Identifier'},
                                        {'name': 'subscription', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Subscription'},
                                        {'name': 'period', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Period'},
                                        {'name': 'category', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Category'},
                                        {'name': 'cmb', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Cmb'},
                                        {'name': 'device', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Device'},
                                        {'name': 'supported_platforms', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Supported Platforms'}
                                    ]

                        },
                        'destinationTable': {
                            'projectId': 'mobbo-dashboard',
                            'datasetId': 'mobbo_dashboard',
                            'tableId': table_name
                        },
                        'sourceFormat': 'CSV',
                        'writeDisposition': "WRITE_TRUNCATE" if truncate else "WRITE_APPEND"
                    }
                }
            },
            media_body=MediaFileUpload(
                csv_path,
                mimetype='application/octet-stream'))

        job = insert_request.execute()

        logger.info('Uploading to BigQuery table %s csv:%s truncate:%s' % (table_name,csv_path,truncate))

        status_request = bigquery.jobs().get(
            projectId=job['jobReference']['projectId'],
            jobId=job['jobReference']['jobId'])

        # Poll the job until it finishes.
        while True:
            result = status_request.execute(num_retries=2)

            if result['status']['state'] == 'DONE':
                if result['status'].get('errors'):
                    raise RuntimeError('\n'.join(
                        e['message'] for e in result['status']['errors']))
                if os.path.isfile(csv_path):
                    os.remove(csv_path)
                logger.info('Uploaded table %s' % table_name)
                return

            time.sleep(1)
    
    @staticmethod
    def insert_googlesalesCSV(csv_path,table,truncate = False,debug = False):

        logger = logging.getLogger('GooglePlayApiLogger')
        bigquery = BigQuery.getService()
        
        table_name = 'debug_'+table if debug else table

        insert_request = bigquery.jobs().insert(
            projectId='mobbo-dashboard',
            body={
                'configuration': {
                    'load': {
                        'schema': {
                            'fields': [
                                        {'name': 'customer_id', 'type': 'INTEGER', 'mode': 'REQUIRED', 'description': 'Customer ID'},
                                        {'name': 'customer_account_id', 'type': 'INTEGER', 'mode': 'REQUIRED','description': 'Customer Account ID'},
                                        {'name': 'order_number', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Order Number'},
                                        {'name': 'charged_date', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable date in UTC (format: YYYY-MM-DD hh:mm:ss)'},
                                        {'name': 'charged_time', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable date in UTC (format: YYYY-MM-DD hh:mm:ss)'},
                                        {'name': 'financial_status', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Financial Status'},
                                        {'name': 'device_model', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Device Model'},
                                        {'name': 'product_title', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Product Title'},
                                        {'name': 'product_id', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Product Id'},
                                        {'name': 'product_type', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Product Type'},
                                        {'name': 'sku_id', 'type': 'STRING', 'mode': 'NULLABLE','description': 'SKU ID'},
                                        {'name': 'sale_currency', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Currency of Sale'},
                                        {'name': 'item_price', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Item Price'},
                                        {'name': 'taxes', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Taxes Collected'},
                                        {'name': 'charged_amount', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Charged Amount'},
                                        {'name': 'developer_proceeds', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Developer Proceeds'},
                                        {'name': 'developer_proceeds_usd', 'type': 'FLOAT', 'mode': 'NULLABLE','description': 'Developer Proceeds USD'},
                                        {'name': 'buyer_city', 'type': 'STRING', 'mode': 'NULLABLE','description': 'City of Buyer'},
                                        {'name': 'buyer_state', 'type': 'STRING', 'mode': 'NULLABLE','description': 'State of Buyer'},
                                        {'name': 'buyer_postal_code', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Postal Code of Buyer'},
                                        {'name': 'buyer_country', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Country of Buyer'},
                                        {'name': 'timestamp', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Unix Timestamp'},
                                        {'name': 'creation_time', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable date in UTC (format: YYYY-MM-DD hh:mm:ss)'},
                                        {'name': 'last_modified', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable date in UTC (format: YYYY-MM-DD hh:mm:ss)'}
                                ]
                        },
                        'destinationTable': {
                            'projectId': 'mobbo-dashboard',
                            'datasetId': 'mobbo_dashboard',
                            'tableId': table_name
                        },
                        'sourceFormat': 'CSV',
                        'writeDisposition': "WRITE_TRUNCATE" if truncate else "WRITE_APPEND"
                    }
                }
            },
            media_body=MediaFileUpload(
                csv_path,
                mimetype='application/octet-stream'))

        job = insert_request.execute()

        logger.info('Uploading to BigQuery table %s csv:%s truncate:%s' % (table_name,csv_path,truncate))

        status_request = bigquery.jobs().get(
            projectId=job['jobReference']['projectId'],
            jobId=job['jobReference']['jobId'])

        # Poll the job until it finishes.
        while True:
            result = status_request.execute(num_retries=2)

            if result['status']['state'] == 'DONE':
                if result['status'].get('errors'):
                    raise RuntimeError('\n'.join(
                        e['message'] for e in result['status']['errors']))
                if os.path.isfile(csv_path):
                    os.remove(csv_path)
                logger.info('Uploaded table %s' % table_name)
                return

            time.sleep(1)
    
    @staticmethod
    def insert_googleinstallCSV(csv_path,table,truncate = False,debug = False):

        logger = logging.getLogger('GooglePlayApiLogger')
        bigquery = BigQuery.getService()
        
        table_name = 'debug_'+table if debug else table

        insert_request = bigquery.jobs().insert(
            projectId='mobbo-dashboard',
            body={
                'configuration': {
                    'load': {
                        'schema': {
                            'fields': [
                                        {'name': 'customer_id', 'type': 'INTEGER', 'mode': 'REQUIRED', 'description': 'Customer ID'},
                                        {'name': 'customer_account_id', 'type': 'INTEGER', 'mode': 'REQUIRED','description': 'Customer Account ID'},
                                        {'name': 'date', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable date in UTC (format: YYYY-MM-DD hh:mm:ss)'},
                                        {'name': 'package_name', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Package Name'},
                                        {'name': 'country', 'type': 'STRING', 'mode': 'NULLABLE','description': 'Country'},
                                        {'name': 'current_device_installs', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Current Device Installs'},
                                        {'name': 'daily_device_installs', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Daily Device Installs'},
                                        {'name': 'daily_device_uninstalls', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Daily Device Uninstalls'},
                                        {'name': 'daily_device_upgrades', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Daily Device Upgrades'},
                                        {'name': 'current_user_installs', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Current User Installs'},
                                        {'name': 'total_user_installs', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Total User Installs'},
                                        {'name': 'daily_user_installs', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Daily User Installs'},
                                        {'name': 'daily_user_uninstalls', 'type': 'INTEGER', 'mode': 'NULLABLE','description': 'Daily User Uninstalls'},
                                        {'name': 'creation_time', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable time in UTC (format: YYYY-MM-DD hh:mm:ss)'},
                                        {'name': 'last_modified', 'type': 'TIMESTAMP', 'mode': 'NULLABLE','description': 'Human readable time in UTC (format: YYYY-MM-DD hh:mm:ss)'}

                                ]
                            },
                        'destinationTable': {
                            'projectId': 'mobbo-dashboard',
                            'datasetId': 'mobbo_dashboard',
                            'tableId': table_name
                        },
                        'sourceFormat': 'CSV',
                        'writeDisposition': "WRITE_TRUNCATE" if truncate else "WRITE_APPEND"
                    }
                }
            },
            media_body=MediaFileUpload(
                csv_path,
                mimetype='application/octet-stream'))

        job = insert_request.execute()

        logger.info('Uploading to BigQuery table %s csv:%s truncate:%s' % (table_name,csv_path,truncate))

        status_request = bigquery.jobs().get(
            projectId=job['jobReference']['projectId'],
            jobId=job['jobReference']['jobId'])

        # Poll the job until it finishes.
        while True:
            result = status_request.execute(num_retries=2)

            if result['status']['state'] == 'DONE':
                if result['status'].get('errors'):
                    raise RuntimeError('\n'.join(
                        e['message'] for e in result['status']['errors']))
                if os.path.isfile(csv_path):
                    os.remove(csv_path)
                logger.info('Uploaded table %s' % table_name)
                return

            time.sleep(1)    
            
    @staticmethod
    def runQuery(query,table_prefix = None):

        big_query = BigQuery.getService()

        query_request = big_query.jobs()
        query_data = {
            'query': query
        }

        query_response = query_request.query(
            projectId='mobbo-dashboard',
            body=query_data).execute()

        return BigQuery.__parseResponse(query_response,table_prefix)

    @staticmethod
    def __parseResponse(resp,table_prefix = None):

        #edge case result is empty
        if int(resp['totalRows']) == 0:
            return []
                
        ret = list()
        
        fields_types = make_fields_dict(resp['schema'])

        for row in resp['rows']:
            item = dict()
            i = 0
            for field in resp['schema']['fields']:

                name = field['name']

                if table_prefix:
                    name = name[len(table_prefix)+1:]

                if fields_types[field['name']] == 'FLOAT':
                    item[name] = float(row['f'][i]['v'])
                elif fields_types[field['name']] == 'INTEGER':
                    item[name] = int(row['f'][i]['v'])
                else:
                    item[name] = row['f'][i]['v']
                i+=1
            ret.append(item)

        return ret
    
def make_fields_dict(schema):
    ret = dict()

    for field in schema['fields']:
        ret[field['name']] = field['type']

    return ret
    
