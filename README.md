# RestCT

**RestCT** is a systematic and automatic black-box testing tool for testing RESTful APIs. This tool takes a Swagger specification file (in JSON format) as the input, and adopts Combinatorial Testing (CT) to automatically generate and send HTTP requests to exercise service behaviours.

For the implementation details of RestCT, please refer to the following paper:

> Huayao Wu, Lixin Xu, Xintao Niu, and Changhai Nie. Combinatorial Testing of RESTful APIs. International Conference on Software Engineerng (ICSE), 2022, accepted



## Usage

### Prerequisite

RestCT requires Python and Java running environemnt (`Python 3.8.2` and `Java 1.8` are used for the development), so please ensure that they are correctly installed and configured in the machine.

Next, run the following command to install Python dependencies (in the root directory of this repo):

```
pip install -r requirements.txt
```

As RestCT relies on [Spacy](https://spacy.io) for constaints extraction, run the following command to download the [trained model](https://spacy.io/models/):

```bash
python -m spacy download en_core_web_sm
```



### Command

Users can run the RestCT tool with the following command:
```bash
python src/restct.py --swagger <abs path> --dir <abs output path>
```
where

- `--swagger` (required): the Swagger specification file of the APIs under test
- `--dir` (required): the root directory of testing results produced

The other optional options supported by RestCT include:

- `--SStrength`: coverage strength of sequence covering arrays for operation (integer), default=2
- `--EStrength`: coverage strength of covering arrays for essential input-parameters (integer), default=3
- `--AStrength`: coverage strength of covering arrays for all input-parameters (integer), default=2
- `--budget`: time budget allocated to perform testing (seconds), default=3600 (one hour)
- `--patterns`: location of the pattern file (used to extract constraints from input-parameters' description), default = `lib/pattern.json`
- `--jar`: location of the ACTS tool (used to generate covering arrays), default=`lib/acts.jar` 
- `--head`: if the APIs under test requires authorization, then the API key shuold be specificed using this option. The format is as `"{\"key\":\"access_token\"}"`
- `--columnId`: is an id that will be part as a column of the statistics file. it is the same as swagger file name if not provided 



### Demo

We provide a simple web service to demonstrate the use of RestCT. The `demo_server/swagger.json` file gives the Swagger specification of this service.

To run this demo, first get into the `demo_server` directory, and start the service:

```bash
cd demo_server
# install dependency packages
pip install -r requirements.txt 
# run the service
python src/app.py
```

Next, run the following command to execute RestCT (in the root directory of this repo):

```bash
python src/restct.py --swagger demo_server/swagger.json --dir demo_server/results
```

During the testing process, the console will print information like the followings (the testing process will terminate in about one minute):

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



### Test Results

When the execution of RestCT finishes, the test results can be found in the `demo_server/results` direcotry. These include:

*  `statistics.csv`: a file that records primary metrics for evaluation, including:
  * coverage strengths applied (*SStrength*=2, *EStrength*=3, and *AStrength*=2, by default)
  * the number of operation sequences generated (*Seq*)
  * average length of each operation sequence (*Len*)
  * 1-way and 2-way sequences that are actually tested (*C_1_way* and *C_2_way*), that is, 2xx or 5xx status code is returned
  * number of all t-way sequences of operations (*All C_SStrength_way*)
  * number of bugs detected (*Bug*)
  * number of HTTP requests generated (*Total*)
  * execution time costs, in seconds (*Cost*) 
* `swagger`
  * `acts`: input and ouput files of the ACTS covering array generator
  * `bug`: detailed information of bugs detected
  * `log`: stdout obtained during the tool execution
  * `unresolvedParams.json`: this file records the set of unsolved parameters during the tool execution

For the above Demo service, RestCT will generate and send around 590 HTTP requests (*Total*). About 50% of operaitons (*C_1_way*), and 17% of 2-way sequence of operations (*C_2_way*) will be acutally tested.



## Replication of Experiment

The Swagger specfications of subject APIs, and scripts to replicate the experiments are availabe in the `exp` directory. Please refer to the [README](/exp/README.md) file for detailed instructions.



## Docker Images for Artifact Evaluation

Additional Docker images are provided to simplify the assesment of the RestCT tool. Please refer to the [README_DOCKER](./README_DOCKER.md) file for detailed instructions.







* src (python codes)

* lib (restct 运行依赖的内容)
  * acts_2.93.jar
  * patterns.json

* demo_server (所有和 demo 相关内容)
  * swagger.json
  * ...
* exp (所有和实验相关的内容)
  * README.md (介绍复现实验的步骤)
  * specifications (11 个 subject)
  * scripts
  * ...
* README.md (介绍工具的基本信息，github repo 的默认展示内容）
* README_DOCKER.md (专门针对 artifact evaluation 的文档，介绍如何基于 docker 使用工具和复现实验)

