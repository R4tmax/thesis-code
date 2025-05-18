from diagrams import Diagram, Cluster, Edge
from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.devtools import Scheduler
from diagrams.gcp.compute import Functions
from diagrams.gcp.security import Iam, ResourceManager
from diagrams.c4 import Person, Container, Database, System, SystemBoundary, Relationship
from diagrams.onprem.client import Users

with Diagram(direction="TB"):
    recipients = Users("Recipients")
    mailgun = System("Mailgun Proxy")
    DWH = BigQuery("BigQuery DWH")

    with Cluster("Auxiliary components"):
        iam = Iam("Cloud IAM")
        secret = ResourceManager("Secret Manager")



    scheduler = Scheduler("Cloud Scheduler\n(CRON)")
    function = Functions("read-and-alert\nCloud Function")

    scheduler >> function >> Edge(label="Get query results") >> DWH
    DWH >> Edge(label="IF results NOT NULL\nTrigger alert") >> mailgun
    mailgun >> Edge(label="Send mail message") >> recipients

    # Optional: link IAM and Secret Manager to function
    function << [iam, secret]
