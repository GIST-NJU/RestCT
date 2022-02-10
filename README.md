# RestCT

**RestCT** is a systematic and automatic black-box testing tool for testing RESTful APIs. This tool takes a Swagger specification file (in JSON format) as the input, and adopts Combinatorial Testing (CT) to automatically generate and send HTTP requests to exercise service behaviours.

For the implementation details of RestCT, please refer to the following paper:

> Huayao Wu, Lixin Xu, Xintao Niu, and Changhai Nie. Combinatorial Testing of RESTful APIs. International Conference on Software Engineering (ICSE), 2022, accepted



## Usage

### Requirement
Linux or MacOs system, we are trying our best to support Windows.

### Setup

RestCT requires Python and Java running environment (`Python 3.8.2` and `Java 1.8` are used for the development), so please ensure that they are correctly installed and configured.

Next, run the following command to install dependency packages (in the root directory of this repo):

```
pip install -r requirements.txt
```

RestCT relies on [Spacy](https://spacy.io), a library of natural language processing, for constraints extraction. Run the following command to download the [trained model](https://spacy.io/models/):

```bash
python -m spacy download en_core_web_sm
```



### Command

Users can run the RestCT tool with the following command:
```bash
python src/restct.py --swagger <path of spec file> --dir <path of output dir>
```
The two mandatory options are:

- `--swagger`: the Swagger specification file of the APIs under test (currently, only OpenAPI 2.0 is supported)
- `--dir`: the output directory of test results

The other optional options include:

- `--SStrength`: coverage strength of sequence covering arrays for operation sequences (Integer), default=2
- `--EStrength`: coverage strength of covering arrays for essential input-parameters (Integer), default=3
- `--AStrength`: coverage strength of covering arrays for all input-parameters (Integer), default=2
- `--budget`: time budget allocated to perform testing (seconds), default=3600 (one hour)
- `--patterns`: location of the pattern file (used to extract constraints from input-parameters' description), default = `lib/matchrules.json`
- `--jar`: location of the ACTS tool (used to generate covering arrays), default=`lib/acts_2.93.jar` 
- `--head`: if the APIs under test requires authorization, then the API key should be specified using this option. The format is as `"{\"key\":\"access_token\"}"`.



### Demo

We provide a simple web service to demonstrate the use of RestCT. The `demo_server/swagger.json` file gives the Swagger specification of this service.

To run this demo, first get into the `demo_server` directory, and start the service:

```bash
cd demo_server
# install dependency packages
pip install -r requirements.txt 
# start the service
python demo_server/app.py
```

Next, run the following command to execute RestCT (in the root directory of this repo):

```bash
python src/restct.py --swagger demo_server/swagger.json --dir demo_server/results
```

The testing process is expected to terminate in about one minute. During this process, the console will print information like the followings:

```
2022-01-25 15:25:55.808 | INFO     | - operations: 6
2022-01-25 15:25:55.808 | INFO     | - examples found: 2
2022-01-25 15:25:55.809 | INFO     | - uncovered combinations: 9, sequence length: 6
2022-01-25 15:25:55.809 | INFO     | - uncovered combinations: 6, sequence length: 6
2022-01-25 15:25:55.810 | INFO     | - uncovered combinations: 3, sequence length: 6
2022-01-25 15:25:55.810 | INFO     | - uncovered combinations: 1, sequence length: 5
2022-01-25 15:25:55.811 | INFO     | - uncovered combinations: 0, sequence length: 3
2022-01-25 15:25:55.811 | DEBUG    | - 1-th operation: post*http://localhost:8888/api/blog/posts
2022-01-25 15:25:56.318 | DEBUG    | -         generate new domains...
2022-01-25 15:25:56.318 | DEBUG    | -             id: 3-{'random', 'default', 'Null'}
2022-01-25 15:25:56.318 | DEBUG    | -             body: 3-{'random', 'default', 'Null'}
```

Once the execution finishes, the test results are saved in the `demo_server/results` directory. The `statistics.csv` file gives the primary metrics for evaluation:

```bash
cat demo_server/results/statistics.csv
```

In this case, RestCT is expected to generate and send around 500+ HTTP requests (*Total*). About 50% of operations (*C_1_way*), and 17% of 2-way sequence of operations (*C_2_way*) can be actually tested.



### Test Results

When the execution of RestCT finishes, the test results can be found in the directory specified by the `--dir` option. These include:

* `statistics.csv`: this file records primary metrics for evaluation, including:
  * coverage strengths applied (*SStrength*=2, *EStrength*=3, and *AStrength*=2, by default)
  * the number of operation sequences generated (*Seq*)
  * average length of each operation sequence (*Len*)
  * 1-way and 2-way sequences that are actually tested (*C_1_way* and *C_2_way*), that is, 2xx or 5xx status code is returned for every operation
  * number of all t-way sequences of operations (*All C_SStrength_way*)
  * number of bugs detected (*Bug*)
  * number of HTTP requests generated (*Total*)
  * execution time costs, in seconds (*Cost*) 
* `swagger`: additional logging files, including:
  * `acts`: input and output files of the ACTS covering array generator
  * `bug`: detailed information of bugs detected
  * `log`: stdout obtained during the tool execution
  * `unresolvedParams.json`: the set of unsolved parameters during the testing process



## Replication of Experiment

The Swagger specifications of subject APIs, and scripts to replicate the experiments are available in the `exp` directory. Please refer to the [README](https://github.com/GIST-NJU/RestCT/blob/main/exp/README.md) file for detailed instructions.



## Docker Image for Artifact Evaluation

Additional Docker images are provided to simplify the assessment of the artifact. Please refer to the [README_DOCKER](https://github.com/GIST-NJU/RestCT/blob/main/README_DOCKER.md) file for detailed instructions.

