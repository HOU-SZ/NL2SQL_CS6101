class BaseInferenceAdapter:
    def __int__(self, **kwargs):
        pass

    def infer(self, prompt: str, **args):
        raise NotImplementedError()
