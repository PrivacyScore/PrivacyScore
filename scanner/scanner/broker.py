from celery import Celery
import config

def getBroker(module):
    app = Celery(module, broker=config.CELERY_BROKER, backend=config.CELERY_BACKEND)
    app.conf.update(
        task_serializer='json',
        accept_content=['json'],  # Ignore other content
        result_serializer='json',
        timezone='Europe/Berlin',
        enable_utc=True,
    )
    app.conf.task_routes = {
    	'scanner.scan_connector.scan_site':  {'queue': 'scan-browser'},
    	'scanner.db_connector.*':            {'queue': 'db-mongo-access'},
    	'scanner.externaltests_connector.*': {'queue': 'scan-external'}
    }
    return app