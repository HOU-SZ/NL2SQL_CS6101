class BaseExpander:
    def expand(self, input_dataset_name_or_path, nl2sql_workdir):
        raise NotImplementedError()

    def name(self):
        raise NotImplementedError()
