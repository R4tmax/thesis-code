from diagrams import Cluster, Diagram, Edge
from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.compute import Functions
from diagrams.gcp.devtools import Scheduler
from diagrams.gcp.security import Iam
from diagrams.gcp.security import ResourceManager
from diagrams.onprem.compute import Server
from diagrams.onprem.client import Users
from diagrams.programming.language import Python

with Diagram("Cloud Alerting Architecture", show=False, direction="LR"):
    recipients = Users("Recipients")
    mailgun_proxy = Server("Mailgun proxy")  # Use a custom icon or use generic server icon


    with Cluster("Cloud Platform"):
        scheduler = Scheduler("Cloud Scheduler (CRON)")
        cloud_func = Functions("read-and-alert\nCloud Functions")

        bq = BigQuery("Source Tables")

        # Auxiliary components
        with Cluster("Auxiliary components"):
            iam = Iam("Cloud IAM")
            secret = ResourceManager("Secret Manager")

    # Flow
    scheduler >> cloud_func
    cloud_func >> Edge(label="2a. Get query results") >> bq
    bq >> Edge(label="1. Pre-created view") >> cloud_func
    cloud_func >> Edge(label="2b. IF NOT NULL,\ntrigger alert") >> mailgun_proxy
    mailgun_proxy >> Edge(label="3. Send mail message") >> recipients
