# Docker Images for Artifact Evaluation

We provide Docker images to simply the assesment of the RestCT tool. In this case, users can skip all prerequisite steps to run the RestCT tool, and also replicate the experiments reported in the paper.



## Setup
docker pull restct and enter it
```bash
docker run --network host -i -t lxxu/restct:1.0 /bin/bash
```


## Use RestCT to Test a Demo Service
To run this demo, first get into the `demo_server` directory, and start the service:

```bash
cd /root/RestCT/demo_server/demo_server

# run the service
nohup python3.8 src/app.py 2>&1 &
```

Next, run the following command to execute RestCT:

```bash
python3.8 /root/RestCT/src/restct.py --swagger /root/RestCT/demo_server/swagger.json --dir /root/RestCT/demo_server/results
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



## Use RestCT to Replicate Experiments
### Test GitLab (6 APIs)

#### Service Deployment
We rely on Docker to deploy and test *GitLab* in a local environemnt. First, run the following command to deploy the service:

```bash
# pull the image
docker pull gitlab/gitlab-ce:13.10.3-ce.0
# run the service
docker run --detach \
    --hostname gitlab.example.com \
    --publish 30001:443 --publish 30000:80 --publish 30002:22 \
    --name gitlab \
    --restart always \
    --volume /srv/gitlab/config:/etc/gitlab \
    --volume /srv/gitlab/logs:/var/log/gitlab \
    --volume /srv/gitlab/data:/var/opt/gitlab \
    --env GITLAB_ROOT_PASSWORD=password1 \
    gitlab/gitlab-ce:13.10.3-ce.0
```

Note that the authentication is required for *GitLab*, and we need to configure it. We use an **OAuth2 token** to authenticate with the API by passing it in the `Authorization` header.

Now, we have an administrator account. Next, we request an `access_token` by sending an HTTP request:

```bash
curl -d 'grant_type=password&username=admin@example.com&password=password1' -X POST http://localhost:30000/oauth/token
```

The response received should like:

```bash
{
 "access_token": "de6780bc506a0446309bd9362820ba8aed28aa506c71eedbe1c5c4f9dd350e54",
 "token_type": "bearer",
 "expires_in": 7200,
 "refresh_token": "8257e65c97202ed1726cf9571600918f3bffb2544b26e00a61df9897668c33a1",
 "created_at": 1607635748
}
```

As such, we can then use the **OAuth2 token** in the header:

```bash
curl --header "Authorization: Bearer OAUTH-TOKEN" "http://localhost:30000/api/v4/projects"
```

Now we return the RestCT container, and check the connection with Gitlab Service:
```bash
ping http://localhost:30000/
```

Generate the experiment scripts for RQ1 and RQ2:
```bash
python3.8 /root/RestCT/exp/scripts.py --gitlabAuth <OAUTH-TOKEN>
```
* Replace `<OAUTH-TOKEN>` with token got above

#### 1. Experiments of RQ1
```bash
cd /root/RestCT/exp/output/GitLab_RQ1
bash /root/RestCT/exp/runScripts/GitLab_RQ1/runAll.sh 2>&1 &
```

#### 2. Experiments of RQ2
```bash
cd /root/RestCT/exp/output/GitLab_RQ2
bash /root/RestCT/exp/runScripts/GitLab_RQ2/runAll.sh 2>&1 &
```

The experiment is not over until the word "Done!" appears in the standard output `./nohup.out`

**The RestCT tool requests the same GitLab server, so the two groups of experiments must not be parallel**

**For RQ1, we commended to use subject `branch`, `commit`,`groups`, or `repository` as a quick assessemnt (about 2~6 minutes for each to execute), because the other two subjects might take about 30 minutes to execute**. 
For example, run the following command to test subject `branch`:
```bash
bash /root/RestCT/exp/runScripts/GitLab_RQ1/scripts/Branch_2_3_2.sh
```
The experiment will end in a few minutes

Once the test execution finishes, several evaluation metrics will be calculated and recorded. See the end of this document for the interpretation of these results.


### Test BingMaps (5 APIs)

#### Service Deployment
We rely on the publicly hosted service of Bing Maps to perform testing, so there is no need to deploy the service.

Authentication is also required for *Bing Maps*. To do this, please register an account at [Bing Maps Dev Center](https://www.bingmapsportal.com/) at first.

Then, apply an API key according to the following steps:

- Sign in to the Bing Maps Dev Center with your Microsoft Account.
- Go to “My Account” and click on “My Keys.”
- Fill out the form and click “Create” and get your API key details.

Generate the experiment scripts for RQ1 and RQ2:
```bash
python3.8 /root/RestCT/exp/scripts.py --bingMapAuth <KEY-TOKEN>
```
* Replace `<OAUTH-TOKEN>` with token got above

#### 1. Experiments of RQ1
```bash
cd /root/RestCT/exp/output/BingMap_RQ1
bash /root/RestCT/exp/runScripts/BingMap_RQ1/runAll.sh 
```

#### 2. Experiments of RQ2
```bash
cd /root/RestCT/exp/output/BingMap_RQ2
bash /root/RestCT/exp/runScripts/BingMap_RQ2/runAll.sh 
```

The experiment is not over until the word "Done!" appears in the standard output 

**Do not run the two groups of experiments in parallel, avoiding affecting the experimental results**

Once the test execution finishes, several evaluation metrics will be calculated and recorded. See the end of this document for the interpretation of these results.


## Experimental Data

When the execution of RestCT finishes, the test results can be found in the `/root/RestCT/exp/output/GitLab[BingMap]_RQ1[RQ2]` direcotry. These include:

* `statistics.csv`: this file records primary metrics for evaluation (tht is, the numbers reported in the paper), including:
  * coverage strengths applied (*SStrength*=2, *EStrength*=3, and *AStrength*=2, by default)
  * the number of operation sequences generated (*Seq*)
  * average length of each operation sequence (*Len*)
  * 1-way and 2-way sequences that are actually tested (*C_1_way* and *C_2_way*)
  * number of all t-way sequences of operations (*All C_SStrength_way*)
  * number of bugs detected (*Bug*)
  * execution time costs, in seconds (*Cost*) 
* `swagger`
  * `acts`: this directory records input and output files of the ACTS covering array generator
  * `bug`: this directory records the detailed information of bugs detected
  * `log`: this directory records the stdout obtained during the tool execution
  * `unresolvedParams.json`: this file records the set of unsolved parameters during the tool execution


## Additional Notes

We note that we cannot guarantee a 100% accurate replication of our experiments in the artifact. As also pointed out by [previous studies](https://github.com/EMResearch/EvoMaster/blob/master/docs/replicating_ studies.md), the approaches of testing RESTful APIs will deal with the networking (non-determinism often occurs), and the algorithm typically involves some levels of randomness. In addition, some subject APIs are remotely deployed web services, and they could be updated frequently. Hence, after running scripts in the artifact, experimental results that are different from those reported in the paper might be observed (especially, when the testing process is only repeated one or two times). Nevertheless, the average results should be similar in most of the times.
