## Grafana Visualization

Grafana serves as the visualization layer for the deployed digital twin system. The **AWS Managed Grafana** is utilized, meaning the service is hosted by AWS.

### Core Infrastructure (Core L5)

The Grafana infrastructure is managed by the **Core L5** deployer, which creates two primary resources:

1.  **Grafana IAM Role:** A dedicated role that allows Grafana to securely access other AWS services like TwinMaker, DynamoDB, and S3.
2.  **Grafana Workspace:** The managed instance of Grafana where dashboards are hosted.

### Authentication and Access

- **AWS SSO:** Authentication is handled through AWS Single Sign-On. After deployment, the manager provides a specific **endpoint URL** for user login.
- **Permissions:** The current execution policy provides broad access to DynamoDB, S3, and TwinMaker. For deployment permissions should be restricted using the principle of least privilege for production environments.
- **Data Path:** Grafana acts as a presentation layer. It does not ingest MQTT messages directly; instead, it fetches data through TwinMaker or directly from DynamoDB to display on dashboards.

### Automation Status

- **Automated:** The system fully automates the creation and deletion of the IAM role, workspace provisioning, and waiting for the workspace to reach an "ACTIVE" status.
- **Manual:** Currently, the deployment of specific dashboards, panels, and the internal configuration of data sources within the Grafana UI are not automated and require manual setup.

---

### Component Overview

| Component          | Description                                             |
| :----------------- | :------------------------------------------------------ |
| **Workspace Name** | Automatically generated as `<digitalTwinName>-grafana`. |
| **Authentication** | Managed via AWS SSO.                                    |
| **Data Sources**   | Connects to AWS IoT TwinMaker, DynamoDB, and S3.        |
| **Primary Role**   | Presentation of modeled data and time-series history.   |
