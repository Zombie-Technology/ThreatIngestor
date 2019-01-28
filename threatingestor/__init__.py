import sys
import time

import threatingestor.config
import threatingestor.state
from threatingestor.exceptions import IngestorError


class Ingestor:

    def __init__(self, config_file):
        # load config
        try:
            self.config = config.Config(config_file)
        except IngestorError as e:
            # error loading config
            sys.stderr.write(e)
            sys.exit(1)

        # load state db
        try:
            self.statedb = threatingestor.state.State(self.config.state_path())
        except (OSError, IOError) as e:
            # error loading state db
            sys.stderr.write(e)
            sys.exit(1)

        # instantiate plugins
        self.sources = dict([(name, source(**kwargs)) for name, source, kwargs in self.config.sources()])
        self.operators = dict([(name, operator(**kwargs)) for name, operator, kwargs in self.config.operators()])

    def run(self):
        if self.config.daemon():
            self.run_forever()
        else:
            self.run_once()

    def run_once(self):
        for source in self.sources:
            # run the source to collect artifacts
            try:
                saved_state, artifacts = self.sources[source].run(self.statedb.get_state(source))
            except Exception as e:
                sys.stderr.write("Unknown error in source {s}: {e}\n".format(s=source, e=e))
                continue

            # save the source state
            self.statedb.save_state(source, saved_state)

            # process artifacts with each operator
            for operator in self.operators:
                try:
                    self.operators[operator].process(artifacts)
                except Exception as e:
                    sys.stderr.write("Unknown error in operator {o}: {e}\n".format(o=operator, e=e))
                    continue

    def run_forever(self):
        while True:
            self.run_once()
            time.sleep(self.config.sleep())

def main():
    if len(sys.argv) < 2:
        print("You must specify a config file")
        sys.exit(1)

    app = Ingestor(sys.argv[1])
    app.run()

if __name__ == "__main__":
    main()
