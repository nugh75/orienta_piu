"""Entry point per python -m src.taskrunner.tui"""

from .app import TaskRunnerTUI


def main():
    app = TaskRunnerTUI()
    app.run()


if __name__ == "__main__":
    main()
