import msvcrt
import subprocess
import sys
import time
from collections.abc import Callable

# Type aliases for clarity
Position = tuple[int, int]
Shape = list[Position]


class Board:
    """재생판을 관리하는 클래스. 경계 검사, 충돌 감지, 렌더링을 담당합니다."""
    
    def __init__(self, width: int = 10, height: int = 20):
        self.width: int = width
        self.height: int = height
        self._grid: list[list[str | None]] = [[None for _ in range(width)] for _ in range(height)]
    
    def is_empty(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and self._grid[y][x] is None
    
    def place_block(self, block: 'Block', x: int, y: int) -> None:
        for dx, dy in block.get_cells():
            self._grid[y + dy][x + dx] = '[]'
    
    def check_collision(self, block: 'Block', x: int, y: int) -> bool:
        for dx, dy in block.get_cells():
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                return True
            if self._grid[ny][nx] is not None:
                return True
        return False
    
    def render(self, current_block: 'Block | None' = None, block_x: int = 0, block_y: int = 0) -> None:
        print('-' * (self.width * 2 + 2))
        for y in range(self.height):
            line: list[str] = []
            for x in range(self.width):
                if current_block and self._is_cell_occupied(current_block, block_x, block_y, x, y):
                    line.append('[]')
                elif self._grid[y][x] is not None:
                    cell = self._grid[y][x]
                    line.append(cell if cell is not None else '  ')
                else:
                    line.append('  ')
            print(f'|{"".join(line)}|')
        print('-' * (self.width * 2 + 2))

    @staticmethod
    def _is_cell_occupied(block: 'Block', bx: int, by: int, x: int, y: int) -> bool:
        for dx, dy in block.get_cells():
            if bx + dx == x and by + dy == y:
                return True
        return False


class Block:
    """블록을 나타내는 클래스. 현재는 1x1 블록이지만, 향후 다양한 모양을 지원하기 위해 설계되었습니다."""
    
    def __init__(self, shape: Shape | None = None):
        self._shape: Shape = shape if shape is not None else [(0, 0)]
    
    def get_cells(self) -> Shape:
        """블록이 차지하는 상대 좌표 목록을 반환합니다."""
        return self._shape
    
    def move(self, dx: int, dy: int) -> 'Block':
        """블록을 주어진 오프셋만큼 이동시킨 새 블록을 반환합니다.
        참고: 불변성 유지 시도. 실제 게임 엔진에서는 블록의 위치를 별도로 관리합니다.
        """
        new_shape = [(x + dx, y + dy) for (x, y) in self._shape]
        return Block(new_shape)
    
    def rotate(self) -> 'Block':
        """블록을 회전시킨 새 블록을 반환합니다. 1x1 블록에서는 변화가 없습니다."""
        # 1x1 블록은 회전해도 동일
        return self


class GameEngine:
    """게임 엔진: 게임 루프, 입력 처리, 중력, 블록 고정 및 재생성을 관리합니다."""
    
    def __init__(self, board: Board | None = None, block_factory: Callable[[], Block] | None = None):
        self._board: Board = board if board is not None else Board()
        self._block_factory: Callable[[], Block] = block_factory if block_factory is not None else (lambda: Block())
        self._current_block: Block | None = None
        self._block_x: int = 0
        self._block_y: int = 0
        self._game_over: bool = False
        self._last_fall_time: float = time.time()
        self._fall_interval: float = 1.0
    
    def _spawn_block(self) -> bool:
        self._current_block = self._block_factory()
        self._block_x = self._board.width // 2 - 1
        self._block_y = 0
        
        # 생성 위치에 이미 블록이 있으면 게임 오버
        if self._board.check_collision(self._current_block, self._block_x, self._block_y):
            self._game_over = True
            return False
        return True
    
    def _handle_input(self) -> None:
        """키보드 입력을 비차단 방식으로 처리합니다."""
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'q' or key == b'Q':
                self._game_over = True
                return
            
            # 현재 블록이 없으면 입력을 무시 (게임 오버 상태 등)
            if self._current_block is None:
                return
            
            # 왼쪽 화살표
            if key == b'\xe0' and msvcrt.kbhit():
                key2 = msvcrt.getch()
                if key2 == b'K':  # 왼쪽
                    new_x = self._block_x - 1
                    if not self._board.check_collision(self._current_block, new_x, self._block_y):
                        self._block_x = new_x
                elif key2 == b'M':  # 오른쪽
                    new_x = self._block_x + 1
                    if not self._board.check_collision(self._current_block, new_x, self._block_y):
                        self._block_x = new_x
                elif key2 == b'P':  # 아래쪽
                    new_y = self._block_y + 1
                    if not self._board.check_collision(self._current_block, self._block_x, new_y):
                        self._block_y = new_y
                        self._last_fall_time = time.time()  # 타이머 리셋
                    else:
                        self._board.place_block(self._current_block, self._block_x, self._block_y)
                        self._current_block = None
    
    def _update_game_state(self) -> None:
        """게임 상태를 업데이트합니다: 자동 낙하, 블록 고정 처리."""
        current_time = time.time()
        if current_time - self._last_fall_time >= self._fall_interval:
            self._last_fall_time = current_time
            
            if self._current_block is None:
                # 블록이 없으면 새로 생성
                if not self._spawn_block():
                    return  # 게임 오버 상태가 설정됨
                return
            
            # 아래쪽으로 한 칸 이동 시도
            new_y = self._block_y + 1
            if not self._board.check_collision(self._current_block, self._block_x, new_y):
                self._block_y = new_y
            else:
                # 더 이상 내려갈 수 없으면 블록을 고정하고 새로운 블록 생성
                self._board.place_block(self._current_block, self._block_x, self._block_y)
                self._current_block = None  # 현재 블록 없음을 표시
                # 다음 루프에서 _spawn_block이 호출되어 새 블록 생성
    
    def run(self) -> None:
        """게임 메인 루프를 실행합니다."""
        if sys.platform == 'win32':
            subprocess.run('', shell=True, check=False)  # Windows VT(ANSI) 활성화
        print('\033[?25l', end='', flush=True)  # 커서 숨김
        if not self._spawn_block():
            self._game_over = True
        
        self._render()
        while not self._game_over:
            self._handle_input()
            self._update_game_state()
            self._render()
            time.sleep(0.01)  # CPU 사용률을 낮게 유지하기 위해 짧은 대기
        
        print('\033[?25h', end='', flush=True)  # 커서 다시 표시
        self._game_over_display()
    
    def _render(self) -> None:
        """현재 게임 상태를 렌더링합니다."""
        sys.stdout.write('\033[H')  # 커서를 홈(좌측 상단)으로 이동
        self._board.render(self._current_block, self._block_x, self._block_y)
        sys.stdout.flush()
    
    def _game_over_display(self) -> None:
        print('\nGame Over!')
        print('Press any key to exit...')
        msvcrt.getch()


def main() -> None:
    """게임의 메인 진입점입니다."""
    try:
        game = GameEngine()
        game.run()
    except KeyboardInterrupt:
        print("\nGame interrupted. Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()