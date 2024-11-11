# CMPUT 455 assignment 4 testing script
# Run using: python3 a4test.py a4.py assignment4-public-tests.txt [-v]

import subprocess
import sys
import time
import signal
import os
import re
import math

TIMELIMIT_COMMANDS = ["genmove", "solve"]
TIMEOUT = 1
DYNAMIC_TIMEOUT = 1
USE_COLOR = True

timelimit_cmd = "timelimit 15"
game_cmd = "game 5 5"
opponent_player = None
student_as_player = 1

if USE_COLOR:
    # Color codes
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    RESET = "\033[0m"
else:
    RED = ""
    GREEN = ""
    BLUE = ""
    RESET = ""

# Functions necessary for checking timeouts
class TimeoutException(Exception):
    pass

def handler(signum, frame):
    raise TimeoutException("Function timed out.")

# Class for specifying tests and recording results
class Test:
    def __init__(self, command, expected, id, to_mark):
        self.command = command
        self.expected = expected
        self.id = id
        self.received = ""
        self.passed = None
        self.matched = None
        self.to_mark = to_mark
        self.notes = ""

    def to_dict(self):
        return {"command": self.command,\
                "expected": self.expected,\
                "id": self.id,\
                "received": self.received,\
                "passed": self.passed,\
                "matched": self.matched,\
                "notes": self.notes}

    # Printed representation of a test
    def __str__(self):
        s = " === Test "+ str(self.id) +" === \nCommand: '" + self.command + "'\nExpected: "
        
        if "\n" in self.expected[:-1]:
            s += "\n'\n" + self.expected + "'\n"
        else:
            s += "'" + self.expected.strip() + "'\n"

        s += "Received: "
        if "\n" in self.received.strip():
            s += "\n'\n"
        else:
            s += "'"

        if self.matched:
            s += f"{GREEN}" + self.received
        else:
            matching = True
            s += f"{GREEN}"
            for i in range(len(self.received.strip())):
                if i < len(self.expected) and self.expected[i] == self.received[i]:
                    if not matching:
                        s += f"{RESET}" + f"{GREEN}"
                else:
                    if matching:
                        s += f"{RESET}" + f"{RED}"
                s += self.received[i]

        if "\n" not in self.received.strip():
            s = s.strip()
        s += f"{RESET}'\n"

        if self.passed and self.matched:
            s += f"{GREEN}+ Success{RESET}\n"
        
        if not self.passed:
            s += f"{RED}- This command failed with error:\n'" + self.notes + f"'{RESET}\n"

        if self.to_mark:
            s += "This command will be marked.\n"
        else:
            s += "This command will NOT be marked.\n"

        return s.strip()+"\n"
    
# Convert a test file into test objects
def file_to_tests(file_name):
    test_lines = []
    with open(file_name, "r") as tf:
        test_lines = tf.readlines()

    i = 0
    while i < len(test_lines):
        # Strip comments
        test_lines[i] = test_lines[i].split("#")[0].strip()
        # Delete whitespace lines
        if len(test_lines[i]) == 0:
            del test_lines[i]
        else:
            i += 1

    # Create tests
    tests = []
    i = 0
    while i < len(test_lines):
        command = test_lines[i]
        i += 1
        expected = test_lines[i] + "\n"
        while test_lines[i][0] != '=':
            i += 1
            expected += test_lines[i] + "\n"
        to_mark = False
        if command[0] == '?':
            to_mark = True
            command = command[1:]
        tests.append(Test(command, expected, len(tests)+1, to_mark))
        i += 1
    return tests

# Send a command, returns whether the command passed, the output received, and any error messages
def send_command(process, command, expected_fail = False, to_mark = False):
    global TIMEOUT, DYNAMIC_TIMEOUT
    if command.split(" ")[0] == "timelimit":
        DYNAMIC_TIMEOUT = int(command.split(" ")[1])
    try:
        process.stdin.write(command+"\n")
        process.stdin.flush()
        output = ""
        try:
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(TIMEOUT) if command.split(" ")[0] not in TIMELIMIT_COMMANDS else signal.alarm(TIMEOUT+DYNAMIC_TIMEOUT)
            line = process.stdout.readline()
            while line[0] != "=":
                if len(line.strip()) > 0:
                    output += line
                line = process.stdout.readline()
            signal.alarm(0)
            output += line

            if '= -1' in line and not expected_fail:
                return False, output, "Command failed with return code -1."
            else:
                return True, output, ""
        
        except TimeoutException:
            return False, output, "Command timeout, exceeded maximum allowed time of " + str(DYNAMIC_TIMEOUT) + " seconds."

    except Exception as e:
        signal.alarm(0)
        return False, "", "Process error:\n" + str(e)

def load_player(proc_name):
    try:
        proc = subprocess.Popen(["python3", proc_name], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(0.1)
        if proc.poll() is not None:
            raise Exception("Program exited with return code: "+str(proc.poll()))
        return proc
    except Exception as e:
        print("Failed to start " + proc_name)
        sys.exit()
        return None

def play_game_send_command(player_tup, cmd):
    player, player_str = player_tup
    if verbose:
        print(player_str, ":", cmd)
    test = Test(cmd, "", 0, False)
    test.passed, test.received, test.notes = send_command(player, test.command)
    if len(test.notes) > 0:
        print(test.notes)
    if verbose or test.command == "show":
        print(test.received.strip())
    test.matched = True
    if player_str == "opponent" and not test.passed:
        print("ERROR: Our testing program had an error.")
        sys.exit()
    return test.passed, test.received

def check_legal_move(move):
    _, received = play_game_send_command((opponent_player, "opponent"), "legal "+move)
    return "yes" in received

def play_game(student_player):
    if opponent_player is None:
        print("ERROR: Opponent player has not been set.")
        sys.exit()

    student_tup = (student_player, "student")
    opponent_tup = (opponent_player, "opponent")

    if student_as_player == 1:
        opponent_as_player = 2
    else:
        opponent_as_player = 1

    passed, _ = play_game_send_command(student_tup, game_cmd)
    if not passed:
        return opponent_as_player
    play_game_send_command(opponent_tup, game_cmd)
    passed, _ = play_game_send_command(student_tup, timelimit_cmd)
    if not passed:
        return opponent_as_player
    play_game_send_command(opponent_tup, timelimit_cmd)

    print("Begin game:\n")
    student_to_play = student_as_player == 1
    while True:
        if student_to_play:
            print("Student program to play:")
            passed, received = play_game_send_command(student_tup, "genmove")
            move = received.split("\n")[0]
            if not passed or "resign" in move or not check_legal_move(move):
                return opponent_as_player
            play_game_send_command(opponent_tup, "play "+move)
        else:
            print("Opponent program to play:")
            _, received = play_game_send_command(opponent_tup, "genmove")
            move = received.split("\n")[0]
            if "resign" in move:
                return student_as_player
            passed, _ = play_game_send_command(student_tup, "play "+move)
            if not passed:
                return opponent_as_player

        play_game_send_command(opponent_tup, "show")
        _, received = play_game_send_command(opponent_tup, "winner")
        if "unfinished" not in received:
            return received.split("\n")[0]
        print()
        student_to_play = not student_to_play

def perform_test(student_player, test):
    global opponent_player, timelimit_cmd, game_cmd, student_as_player
    args = test.command.split(" ")
    test.passed = True
    test.matched = True
    test.received = "= 1\n"
    
    if args[0] == "set_opponent":
        if opponent_player is not None:
            opponent_player.terminate()
        print("Set opponent as:", args[1])
        opponent_player = load_player(args[1])
        return True
    elif args[0] == "game":
        print("Set game command as:", test.command)
        game_cmd = test.command
        return True
    elif args[0] == "timelimit":
        print("Set timelimit command as:", test.command)
        timelimit_cmd = test.command
        return True
    elif args[0] == "set_student_as_player":
        student_as_player = int(args[1])
        if student_as_player == 1:
            print("Set student's program as the first player.")
        else:
            print("Set student's program as the second player.")
        return True
    elif args[0] == "play_game":
        winner = play_game(student_player)
        if str(winner) == str(student_as_player):
            print("The student program wins!")
        else:
            print("The opponent testing program wins.")
        print()
        test.received = str(winner)+"\n= 1\n"
    else:
        test.passed, test.received, test.notes = send_command(student_player, test.command, expected_fail="= -1" in test.expected, to_mark=test.to_mark)

    if test.expected[0] == '@':
        exp_pattern = re.compile((test.expected.strip())[1:], re.DOTALL)
        test.matched = bool(exp_pattern.match(test.received.strip()))
    else:
        test.matched = test.expected == test.received
    return test.matched

# Test a given process on a number of tests. Prints and returns results.
def test_process(student_player, tests, print_output=False):
    t0 = time.time()
    successful = []
    failed = []
    mismatched = []
    test_num = 1

    for test in tests:
        if print_output:
            print("Test", test_num, "/", len(tests), "(" + str(round(100 * test_num / len(tests))) + "%)", end="\r")
        test_num += 1
        perform_test(student_player, test)
        if not test.passed:
            failed.append(test)
        elif not test.matched:
            mismatched.append(test)
        else:
            successful.append(test)        

    if print_output:
        print()
        if verbose:
            for test in tests:
                print(test)

        print(f"{BLUE}\tFailed commands (" + str(len(failed)) + f"):\n{RESET}")
        for test in failed:
            print(test)
        print(f"{BLUE}\tSuccessful commands with mismatched outputs: (" + str(len(mismatched)) + f"):\n{RESET}")
        for test in mismatched:
            print(test)
        print(f"{BLUE}\tSummary report:\n{RESET}")
        print(len(tests), "Tests performed")
        print(f"{GREEN}" + str(len(successful)) + " Successful (" + str(round(100*len(successful) / len(tests))) + f"%){RESET}")
        print(f"{RED}" + str(len(failed)) + " Failed (" + str(round(100*len(failed) / len(tests))) + f"%){RESET}")
        print(f"{RED}" + str(len(mismatched)) + " Mismatched (" + str(round(100*len(mismatched) / len(tests))) + f"%){RESET}")

        print(f"{BLUE}\tMarks report:\n{RESET}")
        passed_marked = len([x for x in successful if x.to_mark])
        all_marked = len([x for x in tests if x.to_mark])
        mark = round(math.floor(passed_marked / all_marked * 20) / 10, 1)
        if mark == 0 and passed_marked != 0:
            mark = 0.1
        print(str(passed_marked) + " / " + str(all_marked) + " marked tests = " + str(mark) + " / 2.0 marks.")
        print("\nFinished in", round(time.time() - t0, 2), "seconds.")

    return successful, failed, mismatched

def test_assignment(proc_name, test_name, marking = False):
    student_player = load_player(proc_name)

    tests = file_to_tests(test_name)

    s, f, m = test_process(student_player, tests, not marking)
    student_player.terminate()
    opponent_player.terminate()
    return s, f, m


if __name__ == "__main__":
    if len(sys.argv) != 3 and (len(sys.argv) != 4 or sys.argv[3] != "-v"):
        print("Usage:\npython3 a1test.py aX.py assignmentX-public-tests.txt [-v]")
        sys.exit()

    verbose = len(sys.argv) == 4 and sys.argv[3] == "-v"
    print_results = True

    if not os.path.isfile(sys.argv[1]):
        print("File '" + sys.argv[1] + "' not found.")
        sys.exit()
    if not os.path.isfile(sys.argv[2]):
        print("File '" + sys.argv[2] + "' not found.")
        sys.exit()

    test_assignment(sys.argv[1], sys.argv[2])