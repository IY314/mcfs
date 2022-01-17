TT_NUM = 'NUM'
TT_LSQ = 'LSQ'
TT_RSQ = 'RSQ'
TT_DOT = 'DOT'
TT_RAW = 'RAW'
TT_SEL = 'SEL'
TT_ID = 'ID'
TT_KW = 'KW'
TT_EOF = 'EOF'

KEYWORDS = [
    'define',
    'as',
    'at',
    'get',
    'set',
    'score',
    'chat',
    'end'
]

SELECTORS = [
    '@e',
    '@a',
    '@p',
    '@r',
    '@s'
]


class Token:
    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        if self.value is not None:
            return f'{self.type}:{self.value}'
        return self.type


def run():
    pass


def main():
    pass


if __name__ == '__main__':
    main()
