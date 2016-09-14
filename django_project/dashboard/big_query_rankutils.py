from oauth2client.client import GoogleCredentials
from googleapiclient import discovery
import logging
import json
import time
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
