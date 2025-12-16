class BNJob:
    def _run_operation(self, operation):
        """Run a single backup operation.
        A job with more than one operation requires multiple calls.

        Args:
            operation (dict): Settings for a single backup operation.
                - "detect_destination_file": ".BackupGoNow-settings.txt",
                - "detect_destination_folder": "3D Models",
                - "source": "\\\\DATACENTER\\3D Models"
        """
        raise NotImplementedError("_run_operation")
