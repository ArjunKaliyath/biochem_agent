from pydantic import BaseModel
import os
import json


class ClusterToModality(BaseModel):
    session_id: str
    cluster_file: str
    modality_file: str

    def __str__(self):
        return f"ClusterToModality(session_id={self.session_id}, cluster_file={self.cluster_file}, modality_file={self.modality_file})"


def initialize_json(session_id: str):
    """
    Initialize the JSON file for storing cluster to modality mappings.
    """
    # os.mkdir(os.path.join(".files", session_id))
    os.makedirs(os.path.join(".files", session_id), exist_ok=True)
    file_path = os.path.join(".files", session_id, "session_data.json")
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump([], f)


def insert_record(session_id: str, cluster_file: str, modality_file: str):
    """
    Insert a record into the JSON file.

    Args:
        session_id (str): Unique identifier for the session.
        cluster_file (str): name of the cluster file.
        modality (str): Modality of the cluster_file.
    """
    file_path = os.path.join(".files", session_id, "session_data.json")
    record = ClusterToModality(
        session_id=session_id, cluster_file=cluster_file, modality_file=modality_file
    )

    with open(file_path, "r+") as f:
        data = json.load(f)
        data.append(record.dict())
        f.seek(0)
        json.dump(data, f, indent=4)


def get_modalities(session_id: str, cluster_file: str):
    """
    Retrieve modality associated with a given session ID and cluster file.

    Args:
        session_id (str): Unique identifier for the session.
        cluster_file (str): Path to the cluster file.

    Returns:
        list: List of modality associated with the session ID and cluster file.
    """
    file_path = os.path.join(".files", session_id, "session_data.json")

    if not os.path.exists(file_path):
        return []

    with open(file_path, "r") as f:
        data = json.load(f)

    return [
        item["modality_file"]
        for item in data
        if item["session_id"] == session_id and item["cluster_file"] == cluster_file
    ]
