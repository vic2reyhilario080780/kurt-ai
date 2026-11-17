"""Zero-markup wallet, verified payment credits and provider API metering."""


class WalletError(RuntimeError):
    no_replay = True

    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__('Kurt Wallet: '+code+'. Request was not replayed.')
