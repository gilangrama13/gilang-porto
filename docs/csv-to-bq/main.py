import os
import logging
import random
from google.cloud import bigquery
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVToBigQueryLoader:
    def __init__(self, project_id, credentials_path=None):
        """
        Initializes the BigQuery client.

        Args:
            project_id (str): Your Google Cloud project ID.
            credentials_path (str, optional): Path to your service account JSON key file.
                                              If None, it uses the default credentials (e.g., set via GOOGLE_APPLICATION_CREDENTIALS).
        """
        self.project_id = project_id
        
        if credentials_path:
            logger.info(f"Using credentials from {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = bigquery.Client(credentials=credentials, project=self.project_id)
        else:
            logger.info("Using default Google Cloud credentials")
            self.client = bigquery.Client(project=self.project_id)

    def load_csv(self, dataset_id, table_id, file_path, schema=None, write_disposition=bigquery.WriteDisposition.WRITE_APPEND):
        """
        Loads a CSV file into a BigQuery table.

        Args:
            dataset_id (str): The ID of the BigQuery dataset.
            table_id (str): The ID of the BigQuery table.
            file_path (str): The local path to the CSV file.
            schema (list, optional): A list of bigquery.SchemaField objects defining the table schema.
                                     If None, BigQuery will attempt to autodetect the schema.
            write_disposition (google.cloud.bigquery.WriteDisposition): Defines what to do if the table already exists.
                                                                       Defaults to WRITE_APPEND.
        """
        table_ref = self.client.dataset(dataset_id).table(table_id)

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,  # Skip the header row
            write_disposition=write_disposition,
        )

        if schema:
            job_config.schema = schema
            logger.info("Using provided schema.")
        else:
            job_config.autodetect = True
            logger.info("Autodetecting schema.")

        logger.info(f"Loading data from {file_path} into {dataset_id}.{table_id}...")
        try:
            with open(file_path, "rb") as source_file:
                job = self.client.load_table_from_file(source_file, table_ref, job_config=job_config)

            # Wait for the job to complete
            job.result()  

            destination_table = self.client.get_table(table_ref)
            logger.info(f"Loaded {destination_table.num_rows} rows into {dataset_id}.{table_id}.")

        except Exception as e:
            logger.error(f"Error loading CSV to BigQuery: {e}")
            raise

def print_ddl_statement(dataset_id, table_id):
    """Prints the DDL statement required to create the BigQuery table."""
    ddl = f"""
    -- DDL to create the table in BigQuery
    CREATE TABLE IF NOT EXISTS `{dataset_id}.{table_id}` (
        id INT64 NOT NULL,
        first_name STRING,
        age INT64,
        city STRING,
        salary FLOAT64,
        is_active BOOL
    );
    """
    print("\n--- BigQuery DDL Statement ---")
    print(ddl)
    print("------------------------------\n")

if __name__ == "__main__":
    # --- Configuration ---
    # Replace these variables with your actual values
    PROJECT_ID = "my-project-id" 
    DATASET_ID = "my_dataset"
    TABLE_ID = "employee" # Updated table name
    CSV_FILE_PATH = "./data/employee.csv"
    
    # Optional: Set this if you are not running in an environment with default credentials
    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/your/service-account-key.json"
    CREDENTIALS_PATH = "./service-account/<my-serviceaccount-key>.json" 

    # Print the DDL needed to create the table
    print_ddl_statement(DATASET_ID, TABLE_ID)

    # Schema Definition corresponding to the new sample data
    custom_schema = [
        bigquery.SchemaField("id", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("first_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("age", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("city", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("salary", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("is_active", "BOOLEAN", mode="NULLABLE"),
    ]

    try:
        # Initialize the loader
        loader = CSVToBigQueryLoader(project_id=PROJECT_ID, credentials_path=CREDENTIALS_PATH)

        # Execute the load
        loader.load_csv(
            dataset_id=DATASET_ID,
            table_id=TABLE_ID,
            file_path=CSV_FILE_PATH,
            schema=custom_schema, # Pass None here to autodetect
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE # Overwrite table if exists
        )
        
    except Exception as e:
        logger.error("Job failed.")
        print(e)