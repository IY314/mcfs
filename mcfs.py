import sys
import string
import json
import re
from dataclasses import dataclass


DIGITS = '0123456789'
LETTERS = string.ascii_letters


def string_with_arrows(text, pos_start, pos_end):
    result = ''

    # Calculate indices
    idx_start = max(text.rfind('\n', 0, pos_start.idx), 0)
    idx_end = text.find('\n', idx_start + 1)
    if idx_end < 0:
        idx_end = len(text)

    # Generate each line
    line_count = pos_end.ln - pos_start.ln + 1
    for i in range(line_count):
        # Calculate line columns
        line = text[idx_start:idx_end]
        col_start = pos_start.col if i == 0 else 0
        col_end = pos_end.col if i == line_count - 1 else len(line) - 1

        # Append to result
        result += line + '\n'
        result += ' ' * col_start + '^' * (col_end - col_start)

        # Re-calculate indices
        idx_start = idx_end
        idx_end = text.find('\n', idx_start + 1)
        if idx_end < 0:
            idx_end = len(text)

    return result.replace('\t', '')


@dataclass
class Position:
    idx: int
    ln: int
    col: int
    fn: str
    ftxt: str

    def advance(self, current_char=None):
        self.idx += 1
        self.col += 1

        if current_char == '\n':
            self.ln += 1
            self.col = 0

    def copy(self):
        return Position(self.idx, self.ln, self.col, self.fn, self.ftxt)


@dataclass
class MCFSError:
    pos_start: Position
    pos_end: Position
    error_name: str
    details: str

    def __repr__(self):
        result = f'{self.error_name}: {self.details}\n'
        result += f'File {self.pos_start.fn}, line {self.pos_start.ln + 1}'
        result += '\n\n' + string_with_arrows(self.pos_start.ftxt, self.pos_start, self.pos_end)
        return result


class MCFSIllegalCharError(MCFSError):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Character', details)


TT_NUM = 'NUM'
TT_LSQ = 'LSQ'
TT_RSQ = 'RSQ'
TT_EQ = 'EQ'
TT_DOT = 'DOT'
TT_RAW = 'RAW'
TT_COMMENT = 'COMMENT'
TT_SEL = 'SEL'
TT_ID = 'ID'
TT_KW = 'KW'
TT_NEWLINE = 'NEWLINE'
TT_JSON = 'JSON'
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


class Token:
    def __init__(self, type_, value=None, pos_start=None, pos_end=None):
        self.type = type_
        self.value = value

        if pos_start:
            self.pos_start = pos_start.copy()
            self.pos_end = pos_start.copy()
            self.pos_end.advance()

        if pos_end:
            self.pos_end = pos_end

    def __repr__(self):
        if self.value is not None:
            return f'{self.type}:{self.value}'
        return self.type


class Lexer:
    def __init__(self, fn, text):
        self.text = text
        self.pos = Position(-1, 0, -1, fn, text)
        self.current_char = None
        self.advance()

    def advance(self):
        self.pos.advance()
        self.current_char = self.text[self.pos.idx] if self.pos.idx < len(self.text) else None

    def make_tokens(self):
        tokens = []

        while self.current_char is not None:
            if self.current_char in ' \t':
                self.advance()
            elif self.current_char == '\n':
                tokens.append(Token(TT_NEWLINE, pos_start=self.pos))
                self.advance()
            elif self.current_char in DIGITS:
                tokens.append(self.make_num())
            elif self.current_char in LETTERS:
                tokens.append(self.make_id())
            elif self.current_char == '@':
                result = self.make_sel()
                if isinstance(result, MCFSError):
                    return [], result
                tokens.append(result)
            elif self.current_char == '(':
                result = self.make_json()
                if isinstance(result, MCFSError):
                    return [], result
                tokens.append(result)
            elif self.current_char == '=':
                tokens.append(Token(TT_EQ, pos_start=self.pos))
                self.advance()
            elif self.current_char == '[':
                tokens.append(Token(TT_LSQ, pos_start=self.pos))
                self.advance()
            elif self.current_char == ']':
                tokens.append(Token(TT_RSQ, pos_start=self.pos))
                self.advance()
            elif self.current_char == '.':
                tokens.append(Token(TT_DOT, pos_start=self.pos))
                self.advance()
            elif self.current_char == '/':
                tokens.append(self.make_raw())
            elif self.current_char == '#':
                pos_start = self.pos.copy()
                pos_end = self.pos.copy()
                self.advance()
                while self.current_char != '#':
                    pos_end.advance()
                    if self.current_char is None:
                        return [], MCFSError(pos_start, pos_end, 'Invalid Syntax', 'Unclosed comment')
                    self.advance()
                self.advance()
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                return [], MCFSIllegalCharError(pos_start, self.pos, f'{char!r}')

        tokens.append(Token(TT_EOF, pos_start=self.pos))
        return tokens, None

    def make_num(self):
        result = ''
        has_dot = False
        pos_start = self.pos.copy()

        while self.current_char is not None and self.current_char in DIGITS + '.':
            if self.current_char == '.':
                if has_dot:
                    break
                has_dot = True
            result += self.current_char
            self.advance()

        return Token(TT_NUM, float(result), pos_start, self.pos)

    def make_id(self):
        result = ''
        pos_start = self.pos.copy()

        while self.current_char is not None and self.current_char in LETTERS + DIGITS:
            result += self.current_char
            self.advance()

        if result in KEYWORDS:
            return Token(TT_KW, result, pos_start, self.pos)
        return Token(TT_ID, result, pos_start, self.pos)

    def make_json(self):
        result = ''
        pos_start = self.pos.copy()

        self.advance()
        while self.current_char is not None and self.current_char != ')':
            result += self.current_char
            self.advance()

        self.advance()

        if not result:
            return MCFSError(pos_start, self.pos, 'Invalid JSON', 'Expected JSON value')

        p = re.compile(r'(\"(.*?)\"|(\w+))(\s*:\s*(\".*?\"|.))')

        return Token(TT_JSON, json.loads(p.sub(r'"\2\3"\4', result)), pos_start, self.pos)

    def make_sel(self):
        result = ''
        pos_start = self.pos.copy()

        result += self.current_char
        self.advance()
        result += self.current_char
        valid = self.current_char is not None and self.current_char in 'pears'
        self.advance()
        if valid:
            return Token(TT_SEL, result, pos_start, self.pos)
        return MCFSError(pos_start, self.pos, 'Invalid selector', f'{result!r}')

    def make_raw(self):
        result = ''
        escaped = False
        pos_start = self.pos.copy()

        while self.current_char is not None and (escaped or self.current_char != '\n'):
            if self.current_char == '\\' and not escaped:
                escaped = True
                continue
            result += self.current_char
            self.advance()

        return Token(TT_RAW, result, pos_start, self.pos)


def run(fn, text):
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    return tokens, error


def main(argv):
    while True:
        text = input('mcfs > ')
        result, error = run('<stdin>', text)
        print(error or result)


if __name__ == '__main__':
    main(sys.argv)
