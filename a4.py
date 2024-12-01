# CMPUT 455 Assignment 4 starter code
# Implement the specified commands to complete the assignment
# Full assignment specification here: https://webdocs.cs.ualberta.ca/~mmueller/courses/cmput455/assignments/a4.html

import sys
import random
import signal
import math
import copy
from collections import defaultdict

# Custom time out exception
class TimeoutException(Exception):
    pass

# Function that is called when we reach the time limit
def handle_alarm(signum, frame):
    raise TimeoutException

class CommandInterface:

    def __init__(self):
        # Define the string to function command mapping
        self.command_dict = {
            "help" : self.help,
            "game" : self.game,
            "show" : self.show,
            "play" : self.play,
            "legal" : self.legal,
            "genmove" : self.genmove,
            "winner" : self.winner,
            "timelimit": self.timelimit
        }
        self.board = [[None]]
        self.player = 1
        self.max_genmove_time = 1
        signal.signal(signal.SIGALRM, handle_alarm)
        self.zobristHashTable = [[None]]
        self.zobristStateHash = 0
        self.numberOfDigitsInRow = [[None]]
        self.numberOfDigitsInCol = [[None]]
    #====================================================================================================================
    # VVVVVVVVVV Start of predefined functions. You may modify, but make sure not to break the functionality. VVVVVVVVVV
    #====================================================================================================================

    # Convert a raw string to a command and a list of arguments
    def process_command(self, str):
        str = str.lower().strip()
        command = str.split(" ")[0]
        args = [x for x in str.split(" ")[1:] if len(x) > 0]
        if command not in self.command_dict:
            print("? Uknown command.\nType 'help' to list known commands.", file=sys.stderr)
            print("= -1\n")
            return False
        try:
            return self.command_dict[command](args)
        except Exception as e:
            print("Command '" + str + "' failed with exception:", file=sys.stderr)
            print(e, file=sys.stderr)
            print("= -1\n")
            return False
        
    # Will continuously receive and execute commands
    # Commands should return True on success, and False on failure
    # Every command will print '= 1' or '= -1' at the end of execution to indicate success or failure respectively
    def main_loop(self):
        while True:
            str = input()
            if str.split(" ")[0] == "exit":
                print("= 1\n")
                return True
            if self.process_command(str):
                print("= 1\n")

    # Will make sure there are enough arguments, and that they are valid numbers
    # Not necessary for commands without arguments
    def arg_check(self, args, template):
        converted_args = []
        if len(args) < len(template.split(" ")):
            print("Not enough arguments.\nExpected arguments:", template, file=sys.stderr)
            print("Recieved arguments: ", end="", file=sys.stderr)
            for a in args:
                print(a, end=" ", file=sys.stderr)
            print(file=sys.stderr)
            return False
        for i, arg in enumerate(args):
            try:
                converted_args.append(int(arg))
            except ValueError:
                print("Argument '" + arg + "' cannot be interpreted as a number.\nExpected arguments:", template, file=sys.stderr)
                return False
        args = converted_args
        return True

    # List available commands
    def help(self, args):
        for command in self.command_dict:
            if command != "help":
                print(command)
        print("exit")
        return True

    def game(self, args):
        if not self.arg_check(args, "n m"):
            return False
        n, m = [int(x) for x in args]
        if n < 0 or m < 0:
            print("Invalid board size:", n, m, file=sys.stderr)
            return False
        
        self.board = []
        for i in range(m):
            self.board.append([None]*n)
        self.player = 1

        self.numberOfDigitsInRow = [[0,0] for i in range(m)]
        self.numberOfDigitsInCol = [[0,0] for i in range(n)]
        self.zobristHashTable = [[ random.randint(-sys.maxsize-1, sys.maxsize) for i in range(3)] for i in range(n*m)]
        self.zobristStateHash=0
        # 0 and 1 in the same position have negated hashcodes
        for i in range(n*m):
            self.zobristStateHash ^= self.zobristHashTable[i][2]
        return True
    
    def show(self, args):
        for row in self.board:
            for x in row:
                if x is None:
                    print(".", end="")
                else:
                    print(x, end="")
            print()                    
        return True
    
    def is_legal_reason(self, x, y, num):
        if self.board[y][x] is not None:
            return False, "occupied"

        consecutive = 0
        count = 0
        self.board[y][x] = num
        for row in range(len(self.board)):
            if self.board[row][x] == num:
                count += 1
                consecutive += 1
                if consecutive >= 3:
                    self.board[y][x] = None
                    return False, "three in a row"
            else:
                consecutive = 0
        too_many = count > len(self.board) // 2 + len(self.board) % 2

        consecutive = 0
        count = 0
        for col in range(len(self.board[0])):
            if self.board[y][col] == num:
                count += 1
                consecutive += 1
                if consecutive >= 3:
                    self.board[y][x] = None
                    return False, "three in a row"
            else:
                consecutive = 0
        if too_many or count > len(self.board[0]) // 2 + len(self.board[0]) % 2:
            self.board[y][x] = None
            return False, "too many " + str(num)

        self.board[y][x] = None
        return True, ""

    def is_legal(self, x, y, num):
        if self.board[y][x] is not None:
            return False
         
        if self.violatesTriplesConstraint(x, y, num, self.board, len(self.board[0]), len(self.board)):
            return False
        if self.violatesBalanceConstraint(x, y, num):
            return False
        return True

    def violatesBalanceConstraint(self, col, row, digit):
        # Get number of value element (0 or 1) in the target row and column
        # Add 1 to the count to account for the new value being added
        digitsInRow = self.numberOfDigitsInRow[row][digit] + 1
        digitsInCol = self.numberOfDigitsInCol[col][digit] + 1
        # If the number of value elements in the row or column exceeds half the size of the row or column return True
        boardWidth = len(self.board[0])
        boardHeight = len(self.board)
        if math.ceil(boardWidth / 2) < digitsInRow:
            return True
        if math.ceil(boardHeight / 2) < digitsInCol:
            return True

        return False

    def violatesTriplesConstraint(self, col, row, digit, board, boardWidth, boardHeight):
        if (
            row < 0
            or col < 0
            or (digit != 1 and digit != 0)
            or row >= boardHeight
            or col >= boardWidth
            or len(board)*len(board[0]) != boardWidth * boardHeight
        ):
            raise Exception("Invalid argument for violatesTriplesConstraint() function")

        pointerRight = col
        while (pointerRight+1 < boardWidth and board[row][pointerRight+1] == digit):
            pointerRight += 1
            if pointerRight - col + 1 >= 3:
                return True

        pointerLeft = col
        while(pointerLeft - 1>=0 and board[row][pointerLeft-1] == digit):
            pointerLeft -= 1
            if col - pointerLeft + 1 >= 3:
                return True

        if pointerRight - pointerLeft + 1 >= 3:
            return True

        pointerUp = row
        while (pointerUp - 1 >= 0 and board[pointerUp-1][col] == digit):
            pointerUp -= 1
            if row - pointerUp + 1 >= 3:
                return True

        pointerDown = row
        while (pointerDown+1 < boardHeight and board[pointerDown+1][col] == digit):
            pointerDown += 1
            if pointerDown - row + 1 >= 3:
                return True

        if pointerDown - pointerUp + 1 >= 3:
            return True

        return False
    
    def valid_move2(self, x, y, num):
        if  x >= 0 and x < len(self.board[0]) and\
                y >= 0 and y < len(self.board) and\
                (num == 0 or num == 1):
            legal, _ = self.is_legal(x, y, num)
            return legal

    def valid_move(self, x, y, num):
        return  x >= 0 and x < len(self.board[0]) and\
                y >= 0 and y < len(self.board) and\
                (num == 0 or num == 1) and\
                self.is_legal(x, y, num)

    def play(self, args):
        err = ""
        if len(args) != 3:
            print("= illegal move: " + " ".join(args) + " wrong number of arguments\n")
            return False
        try:
            x = int(args[0])
            y = int(args[1])
        except ValueError:
            print("= illegal move: " + " ".join(args) + " wrong coordinate\n")
            return False
        if  x < 0 or x >= len(self.board[0]) or y < 0 or y >= len(self.board):
            print("= illegal move: " + " ".join(args) + " wrong coordinate\n")
            return False
        if args[2] != '0' and args[2] != '1':
            print("= illegal move: " + " ".join(args) + " wrong number\n")
            return False
        num = int(args[2])
        legal, reason = self.is_legal_reason(x, y, num)
        if not legal:
            print("= illegal move: " + " ".join(args) + " " + reason + "\n")
            return False
        self.board[y][x] = num
        # Increment row and column number of digits tracker
        col = x
        row = y
        self.numberOfDigitsInRow[row][num] += 1
        self.numberOfDigitsInCol[col][num] += 1
        self.zobristStateHash ^= self.zobristHashTable[len(self.board[0])*row+col][2] ^ self.zobristHashTable[len(self.board[0])*row+col][num]
        if self.player == 1:
            self.player = 2
        else:
            self.player = 1
        return True

    def play2(self, args):
        err = ""
        if len(args) != 3:
            print("= illegal move: " + " ".join(args) + " wrong number of arguments\n")
            return False
        try:
            x = int(args[0])
            y = int(args[1])
        except ValueError:
            print("= illegal move: " + " ".join(args) + " wrong coordinate\n")
            return False
        if  x < 0 or x >= len(self.board[0]) or y < 0 or y >= len(self.board):
            print("= illegal move: " + " ".join(args) + " wrong coordinate\n")
            return False
        if args[2] != '0' and args[2] != '1':
            print("= illegal move: " + " ".join(args) + " wrong number\n")
            return False
        num = int(args[2])
        legal, reason = self.is_legal(x, y, num)
        if not legal:
            print("= illegal move: " + " ".join(args) + " " + reason + "\n")
            return False
        self.board[y][x] = num
        col = x
        row = y
        self.numberOfDigitsInRow[row][num] += 1
        self.numberOfDigitsInCol[col][num] += 1
        # print("Custom Play yeehaw")
        if self.player == 1:
            self.player = 2
        else:
            self.player = 1
        return True
    
    def legal(self, args):
        if not self.arg_check(args, "x y number"):
            return False
        x, y, num = [int(x) for x in args]
        if self.valid_move(x, y, num):
            print("yes")
        else:
            print("no")
        return True
    
    def get_legal_moves(self):
        moves = []
        for y in range(len(self.board)):
            for x in range(len(self.board[0])):
                for num in range(2):
                    if self.is_legal(x, y, num):
                        moves.append([str(x), str(y), str(num)])
        return moves

    def get_legal_moves2(self):
        moves = []
        for y in range(len(self.board)):
            for x in range(len(self.board[0])):
                for num in range(2):
                    legal, _ = self.is_legal(x, y, num)
                    if legal:
                        moves.append([str(x), str(y), str(num)])
        return moves

    def winner(self, args):
        if len(self.get_legal_moves()) == 0:
            if self.player == 1:
                print(2)
            else:
                print(1)
        else:
            print("unfinished")
        return True

    def timelimit(self, args):
        self.max_genmove_time = int(args[0])
        return True

    #===============================================================================================
    # ɅɅɅɅɅɅɅɅɅɅ End of predefined functions. ɅɅɅɅɅɅɅɅɅɅ
    #===============================================================================================

    #===============================================================================================
    # VVVVVVVVVV Start of Assignment 4 functions. Add/modify as needed. VVVVVVVV
    #===============================================================================================
    def genmove2(self, args):
        try:
            # Set the time limit alarm
            signal.alarm(self.max_genmove_time)
            
            # Modify the following to give better moves than random play 
            moves = self.get_legal_moves()
            if len(moves) == 0:
                print("resign")
            else:
                rand_move = moves[random.randint(0, len(moves)-1)]
                self.play(rand_move)
                print(" ".join(rand_move))
            
            # Disable the time limit alarm 
            signal.alarm(0)

        except TimeoutException:
            # This block of code runs when the time limit is reached
            print("resign")

        return True

    def genmove(self, args):
        debug = 1

        # Initialize tree
        tree = {}

        # Save root data
        rootBoard = copy.deepcopy(self.board)
        rootPlayer = copy.deepcopy(self.player)
        rootStateHash = copy.deepcopy(self.zobristStateHash)
        rootNumDigitsRow = copy.deepcopy(self.numberOfDigitsInRow)
        rootNumDigitsCol = copy.deepcopy(self.numberOfDigitsInCol)

        if debug == 1:
            
            root_details= self.get_root_details(rootBoard, rootPlayer, rootNumDigitsRow, rootNumDigitsCol)
        try:
            # Set the time limit alarm
            signal.alarm(self.max_genmove_time)
            
            # Modify the following to give better moves than random play 
            moves = self.get_legal_moves()

            if len(moves) == 0:
                print("resign")
            else:
                self.run_mcts_loop(tree)   
            # Disable the time limit alarm 
            signal.alarm(0)

        except TimeoutException:
            self.resetRootState(rootBoard, rootPlayer, rootStateHash,  rootNumDigitsRow, rootNumDigitsCol)
            move = self.final_move_select(tree, moves)
            if debug == 1:
                mcts_details = self.get_mcts_details(tree, moves)
            self.play(move)
            print(" ".join(move))
        if debug == 1:
            print(root_details)
            print(mcts_details)
        return True

    def get_root_details(self, rootBoard, rootPlayer, rootNumDigitRow, rootNumDigitCol):
        out = ""
        out += "Root board state: \n"
        for row in rootBoard:
            for x in row:
                if x is None:
                    out += "."
                else:
                    out += str(x)
            out += "\n"
        out += "Root player: \n"
        out += str(rootPlayer) + "\n"
        out += "Root numOfDigitsInRow: \n"
        out += str(rootNumDigitRow)+"\n"
        out += "Root numOfDigitsInCol: \n"
        out += str(rootNumDigitCol)+" \n"
        return out
    
    def run_mcts_loop(self, tree):
        mcts_solver_output = 0
        counter = 0
        
        self.addToTree(tree)

        while True: 
        # while counter <= 0:
            mcts_solver_output = self.MCTSSolver(tree)
            counter += 1
        
        return True 
    
    def get_mcts_details(self, tree, legal_moves):
        total_children_visits = 0
        out = "Moves detail: \n"

        for move in legal_moves:
            self.simulateMove(move)
            childHash = self.getStateHash()
            self.undoSimulatedMove(move)
            if childHash not in tree:
                out+="Move: "+str(move)+" not added to tree\n"
                continue
            total_children_visits += tree[childHash]['visits']
            value = (tree[childHash]['wins']/tree[childHash]['visits'] - (0.7)/math.sqrt(tree[childHash]['visits']))
            out+="Move: "+ str(move)+ " Value: "+ str(value) +" "+ str(tree[childHash])+"\n"
        return out
    
    def resetRootState(self, rootBoard, rootPlayer, rootStateHash, rootNumDigitsRow, rootNumDigitsCol):
        self.board = rootBoard
        self.player = rootPlayer
        self.zobristStateHash = rootStateHash
        self.numberOfDigitsInRow = rootNumDigitsRow
        self.numberOfDigitsInCol = rootNumDigitsCol

    # O(n)
    def final_move_select(self, tree, legal_moves):
        best_measure = float('-inf')
        final_move = None

        for move in legal_moves:
            self.simulateMove(move)
            simulatedStateHash = self.getStateHash()
            self.undoSimulatedMove(move)
            if simulatedStateHash not in tree:
                continue
            current_measure = (tree[simulatedStateHash]['wins']/tree[simulatedStateHash]['visits'] - (0.7)/math.sqrt(tree[simulatedStateHash]['visits'])) 
            if current_measure >= best_measure:
                best_measure = current_measure
                final_move = move
        return final_move

    def getStateHash(self):
        # return str(self.board)
        return self.zobristStateHash

    # O(d * n^2)
    def MCTSSolver(self, tree):
        legal_moves = self.get_legal_moves()
        currentStateHash = self.getStateHash()
        
        tree[currentStateHash]['visits']+=1

        if len(legal_moves) <= 0:
            tree[currentStateHash]['wins'] = float('inf')
            return float('-inf')
        
        best_child_move = self.selectBestChildNode(tree, legal_moves)
        self.simulateMove(best_child_move)
        best_child_hash = self.getStateHash()
        self.undoSimulatedMove(best_child_move)

        if(best_child_hash not in tree):

            R = -self.playOut(best_child_move, legal_moves)
            
            self.simulateMove(best_child_move)
            self.addToTree(tree)
            tree[best_child_hash]['visits'] += 1
            tree[best_child_hash]['wins'] += (1 if R == 1 else 0)
            self.undoSimulatedMove(best_child_move)

            tree[currentStateHash]['wins'] += (1 if R == -1 else 0)
            return R

        if(tree[best_child_hash]['wins'] != float('-inf') and tree[best_child_hash]['wins'] != float('inf')):
            self.simulateMove(best_child_move)
            R = -self.MCTSSolver(tree)
            self.undoSimulatedMove(best_child_move)
        else:
            R = tree[best_child_hash]['wins']
            
        if(R == float('inf')):
            tree[currentStateHash]['wins'] = float('-inf')
            return R
        else:
            if(R == float('-inf')):
                for move in legal_moves:
                    self.simulateMove(move)
                    childHash = self.getStateHash()
                    self.undoSimulatedMove(move)
                    if (tree[childHash]['wins'] != R):
                        R = -1
                        tree[currentStateHash]['wins'] += 1
                        return R
                tree[currentStateHash]['wins'] = float('inf')
                return R
            else:
                tree[currentStateHash]['wins'] += (1 if R == -1 else 0)
                return R

    # O(1)
    def simulateMove(self, move):
        col = int(move[0])
        row = int(move[1])
        digit = int(move[2])
        self.board[row][col] = digit
        self.player = self.changePlayerTurn(self.player)
        self.numberOfDigitsInRow[row][digit] += 1
        self.numberOfDigitsInCol[col][digit] += 1
        self.zobristStateHash ^= self.zobristHashTable[len(self.board[0])*row+col][2] ^ self.zobristHashTable[len(self.board[0])*row+col][digit]

    #O(1)
    def undoSimulatedMove(self, move):
        col = int(move[0])
        row = int(move[1])
        digit = int(move[2])
        self.board[row][col] = None
        self.player = self.changePlayerTurn(self.player)
        self.numberOfDigitsInRow[row][digit] -= 1
        self.numberOfDigitsInCol[col][digit] -= 1
        self.zobristStateHash ^= self.zobristHashTable[len(self.board[0])*row+col][2] ^ self.zobristHashTable[len(self.board[0])*row+col][digit]

    # Time complexity : O(n^2)
    def playOut(self, best_child_move, legal_moves):
        self.simulateMove(best_child_move)

        best_child_player = copy.deepcopy(self.player)
    
        move_stack = [best_child_move]
        
        while True:
            if len(legal_moves) <= 0:
                break
            rand_idx = random.randint(0, len(legal_moves)-1)
            rand_move = legal_moves[rand_idx]
            col = int(rand_move[0])
            row = int(rand_move[1])
            num = int(rand_move[2])
            legal_moves[rand_idx] = legal_moves[-1]
            legal_moves.pop()
            if not self.is_legal(col, row, num):    
                continue
            self.simulateMove(rand_move)
            move_stack.append(rand_move)
        
        if(self.player == best_child_player):
            for move in move_stack:
                # undo move
                self.undoSimulatedMove(move)
            return -1
        else:
            for move in move_stack:
                # undo move
                self.undoSimulatedMove(move)
            return 1
    
    def changePlayerTurn(self, playerVar):
        if playerVar == 1:
            return 2
        elif playerVar == 2:
            return 1
        else:
            raise Exception("Unhandled error at changePlayerTurn()")

    def heuristic(self, move):
        col = int(move[0])
        row = int(move[1])
        digit = int(move[2])
        h = self.numberOfDigitsInRow[row][digit] + self.numberOfDigitsInCol[col][digit]
        return h

    # Return best child of a node. Time Complexity:  O(n^2).
    def selectBestChildNode(self, tree, legal_moves):
        best_value = float('-inf')
        ties = []
        currentStateHash = self.getStateHash()

        for move in legal_moves:

            self.simulateMove(move)
            simulatedStateHash = self.getStateHash()
            self.undoSimulatedMove(move)
            total_parent_visits = tree[currentStateHash]['visits']
            if simulatedStateHash not in tree:
                ties =[move]
                break
            current_node_visits = tree[simulatedStateHash]['visits']
            c = 10
            k = 0
            exploitation = tree[simulatedStateHash]['wins']/tree[simulatedStateHash]['visits'] + k * self.heuristic(move)
            exploration = c * math.sqrt(math.log(total_parent_visits) / (current_node_visits))

            if exploitation+exploration > best_value:
                best_value = exploitation+exploration
                ties=[move]

            if exploitation+exploration == best_value:
                ties.append(move)

        return random.choice(ties)
            
    # Add node to tree. Time Complexity: O(n^2)
    def addToTree(self, tree):
        currentStateHash = self.getStateHash()
        if currentStateHash in tree:
            return
        tree[currentStateHash] = {
                'wins':0,
                'visits':0
        }



    #===============================================================================================
    # ɅɅɅɅɅɅɅɅɅɅ End of Assignment 4 functions. ɅɅɅɅɅɅɅɅɅɅ
    #===============================================================================================
    
if __name__ == "__main__":
    interface = CommandInterface()
    interface.main_loop()
