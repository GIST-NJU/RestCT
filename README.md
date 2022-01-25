# Artifact of "Combinatorial Testing of RESTful APIs"

## Overview

This paper presents RestCT, a systematic and fully automatic approach that adopts Combinatorial Testing (CT) to test RESTful APIs. 
RestCT is systematic in that it covers and tests not only the interactions of a certain number of operations in RESTful APIs, 
but also the interactions of particular input-parameters in every single operation. 
This is realised by a novel two-phase test case generation approach, 
which first generates a constrained sequence covering array to determine the execution orders of available operations,
and then applies an adaptive strategy to generate and refine several constrained covering arrays to concretise input-parameters of each operation. 
RestCT is also automatic in that its application relies on only a given Swagger specification of RESTful APIs. 
The creation of CT test models (especially, the inferring of dependency relationships in operation and input-parameter levels), 
and the generation and execution of test cases are performed without any human intervention. 

## Important Files
This artifact includes:

- The `src` folder contains source codes that implements RestCT tool, the testing approach proposed in the paper "Combinatorial Testing of RESTful APIs". This tool takes a Swagger specification file as input, and then adopts combinatorial testing to generates concrete HTTP requests to test RESTful APIs described in the specification.
- The `swagger` folder contains the 11 Swagger specifications are created to test APIs of two real-world service systems, GitLab and Bing Maps. The experimental results reported in the paper are obtained based on these specifications.
- The `exp` folder contains the experiment scripts we used to obtain the experimental results reported in the paper
- The `demo_server` folder contains a simple RESTful API system demo. Read the `demo_server/README.md` for more details

## How To Use RESTCT
### Set Up RESTCT

- Python 3.8.2 and Java 1.8 for your appropriate OS
- Switch to the repo root directory and install Python dependencies
    ```bash
    pip install -r requirements.txt
    ```
- Download trained models for [Spacy](https://spacy.io/models/)
    ```bash
    python -m spacy download en_core_web_sm
    ```

### Command
Users can run the RestCT tool with the following command:
```bash
python restct.py  RESTCT [-h] --swagger SWAGGER --dir DIR [--SStrength SSTRENGTH] [--EStrength ESTRENGTH] [--AStrength ASTRENGTH] [--budget BUDGET] [--patterns PATTERNS] [--jar JAR] [--header HEADER] [--columnId COLUMNID]
```
#### Console Options
- `--swagger` indicates the Swagger specification file of the APIs under test
- `--dir` indicates where the experimental data is stored
- `--SStrength`(int) is the strength of **operation sequence covering array**, default=2
- `--EStrength`(int) is the strength of **essential input-parameters covering array**, default=3
- `--AStrength`(int) is the strength of **all input-parameters covering array**, default=2
- `--budget` specifies maximum amount of time(seconds) allowed for the testing, default=3600(1 hour)
- `--patterns` provides the patterns used in testing to extract constraints from input-parameters' description
- `--jar` provides the ACTS jar file used in generating input-parameter covering array
- `--head` is needed if the APIs under test ask for authorization. The format is `"{\"key\":\"access_token\"}"`
- `--columnId` is an id that will be part as a column of the statistics file. it is the same as swagger file name if not provided 

For example, if demo_sever has been deployed successfully, we can test it using the following command:
```bash
python restct.py --swagger <parent directory>/RestCT/swagger/Demo/swagger.json --dir <parent directory>/RestCT/output --jar <parent directory>/RestCT/acts_2.93.jar
```
When the testing ends, you should see coverage information and other information in `RestCT/output/statistics.csv`.

## Obtain the Artifact

The artifact is publicly accessible, which can be downloaded from one of the following websites:

* GitHub repository: https://github.com/GIST-NJU/RestCT (tag: 1.0)
* Zendo: https://xxxx

For the installation and usage of the RestCT tool, please see `install.md` file. The Swagger specifications are all in JSON format, which can be handled in a simple text editor.

The directories of this artifcat are organised as follows:

* 1
* 2
* 3


## Replicating 

In the experiment, RestCT is applied to test APIs of two service systems, GitLab (a local version is deployed as GitLab is an open source project) and Bing Maps (the remote service is used as the subject).

### Test GitLab (6 APIs)

The Docker environment is required to deploy GitLab. So, please deploy the docker image of specified version `13.10.3-ce.0` at first:

```bash
sudo docker run --detach \
  --hostname gitlab.example.com \
  --publish 30003:443 --publish 30000:80 --publish 30002:22 \
  --name gitlab \
  --restart always \
  --volume /Users/lixin/Desktop/gitlab-ce/config:/etc/gitlab \
  --volume /Users/lixin/Desktop/gitlab-ce/logs:/var/log/gitlab \
  --volume /Users/lixin/Desktop/gitlab-ce/data:/var/opt/gitlab  \
  --env GITLAB_ROOT_PASSWORD=password1 \
  gitlab/gitlab-ce: 13.10.3-ce.0
```
To publish a port for container, we use `--publish` flag on the docker run command. The format of the `--publish` command is `[host port]:[container port]`. 
So if we want the base url of the API to be same as described in the swagger, we have to expose port 80 inside the container to port 30000 outside the container, `--publish 30000:80`.

Next, Authentication Configuration. We use an **OAuth2 token** to authenticate with the API by passing it in the `Authorization` header. We have set the root password via `--env` in docker run command, 
then we request an `access_token` with HTTP request

```python
import requests

account = {
          "grant_type": "password",
          "username": "admin@example.com", 
          "password": "password1"
        }

header = {'Content-Type': 'application/json'}

# the baseurl depends on `[host port]:80` passed to `--publish` flag
# the default is http://localhost:30000/
oauth = requests.post('http://localhost:30000/oauth/token', json=account, headers=header)

oauth.json()
```
Example response:
```bash
{
 "access_token": "de6780bc506a0446309bd9362820ba8aed28aa506c71eedbe1c5c4f9dd350e54",
 "token_type": "bearer",
 "expires_in": 7200,
 "refresh_token": "8257e65c97202ed1726cf9571600918f3bffb2544b26e00a61df9897668c33a1",
 "created_at": 1607635748
}
```
Example of using the `OAuth2 token` in a header
```bash
curl --header "Authorization: Bearer OAUTH-TOKEN" "https://gitlab.example.com/api/v4/projects"
```

Finally, run the following command to use RestCT to test each subject API of GitLab:

```bash
python replicate_gitlab.py [subject] [coverage]
```

* `subject` indicates the name of the subject API, which can be `branch`, `projects`, ...
* `coverage` 

Once the execution finishes, statistics of the testing results will be printed in the stdout (from which the data reported in the paper can be extracted). An additional data file `[subject].csv` will also be produced.

**Note**: it will take about one hour to test each subject API.



### Test BingMaps (5 APIs)

We rely on the remote service of Bing Maps to perform testing. So, please register at [Bing Maps Dev Center](https://www.bingmapsportal.com/) and apply an API key at first. The specific steps are:
- Sign in to the Bing Maps Dev Center with your Microsoft Account.
- Go to “My Account” and click on “My Keys.”
- Fill out the form and click “Create” and get your API key details.

Similarly, run the following command to use RestCT to test each subject API of Bing Maps:

```bash
python replicate_bingmaps.py [subject] [coverage]
```

* `subject` indicates the name of the subject API, which can be ...
* `coverage` 

Once the execution finishes, statistics of the testing results will be printed in the stdout (from which the data reported in the paper can be extracted). An additional data file `[subject].csv` will also be produced.

**Note**: it will take about one hour to test each subject API.



#### Experimental Data

After the testing of each subject API, the stdout will print the following data ():

* The number of operation sequences generated
* The average length of all operation sequences
* ...

The `subject.csv` file ...

