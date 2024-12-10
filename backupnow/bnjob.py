class BNJob:
    def _run_operation(self, operation):
        """Run a backup operation.

        Args:
            operation (dict): _description_
                - "detect_destination_file": ".BackupGoNow-settings.txt",
                - "detect_destination_folder": "3D Models",
                - "source": "\\\\DATACENTER\\3D Models"
        """
        raise NotImplementedError("_run_operation")
