import os


class BNJob:
    def _run_operation(self, operation, destination):
        """Run a single backup operation.
        A job with more than one operation requires multiple calls.

        Args:
            operation (dict): Settings for a single backup operation.
                - "detect_destination_file": ".BackupGoNow-settings.txt",
                - "detect_destination_folder": "3D Models",
                - "detect_source_folder": "Design and Development",
                - "source": "\\\\DATACENTER\\3D Models"
        """
        detect_dst_file = operation.get('detect_destination_file')
        detect_dst_dir = operation.get('detect_destination_folder')
        detect_names = []
        found_dst_paths = []
        assert destination is not None
        assert os.path.isdir(destination)
        if detect_dst_dir:
            detect_names.append(detect_dst_dir)
            detect_dst_path = os.path.join(destination, detect_dst_dir)
            if os.path.isdir(detect_dst_path):
                found_dst_paths.append(detect_dst_dir)
        if detect_dst_file:
            detect_names.append(detect_dst_file)
            detect_dst_path = os.path.join(destination, detect_dst_file)
            if os.path.isfile(detect_dst_path):
                found_dst_paths.append(detect_dst_file)
        if detect_names:
            if not found_dst_paths:
                raise ValueError("There is no {} on {}"
                                 .format(detect_names, destination))
        raise NotImplementedError("_run_operation")
