# Docker Image for Artifact Evaluation

We provide a Docker image, `restct`, to simply the assessment of the RestCT tool. In this case, users can skip environment settings to run the RestCT tool, and also replicate the experiments reported in the paper. *At present, we only provide `restct` docker image for `linux/amd64`.*

A copy of this image is also archived at DOI [10.5281/zenodo.5909761](https://doi.org/10.5281/zenodo.5909761).




## Setup

Pull the `restct`  image and start the container:

```bash
docker pull lxxu/restct:latest
docker run --network host -i -t lxxu/restct:latest /bin/bash
```

The source codes of the RestCT repository (https://github.com/GIST-NJU/RestCT) can be found in `\root\RestCT`.



## Use RestCT to Test a Demo Service

**The commands in this section should be executed inside the `restct` container**.

First, get into the `demo_server` directory, and start the [demo service](https://github.com/microsoft/restler-fuzzer/tree/main/demo_server) (this service comes from the [restler-fuzzer](https://github.com/microsoft/restler-fuzzer) project):

```bash
cd /root/RestCT/demo_server
nohup python3.8 demo_server/app.py 2>&1 &
```

Next, run the following command to apply RestCT to test the service:

```bash
python3.8 /root/RestCT/src/restct.py --swagger /root/RestCT/demo_server/swagger.json --dir /root/RestCT/demo_server/results
```

Here, `--swagger` indicates the Swagger specification file of the APIs under test, and `--dir` indicates the output directory of test results. Please refer to the [README](https://github.com/GIST-NJU/RestCT/blob/main/README.md) file for more available options. 

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
cat /root/RestCT/demo_server/results/statistics.csv
```

In this case, RestCT is expected to generate and send around 500+ HTTP requests (*Total*). About 50% of operations (*C_1_way*), and 17% of 2-way sequence of operations (*C_2_way*) can be actually tested. The detailed interpretation of the test results can be found at the end of this document.



## Use RestCT to Replicate Experiments
In our experiment, the performance of RestCT is evaluated under 11 real-world subject APIs of two service systems, *GitLab* and *Bing Maps*. The Swagger specifications of these subject APIs are available in the `/root/RestCT/exp/swagger` directory. 



### 1. Setup GitLab

**The following commands should be executed in the host machine (outside the `restct` container)**.

We rely on Docker to deploy GitLab in the local environment. Run the following command to download and start a GitLab container (this initialization process may take several minutes, please wait until the status of the container becomes *healthy*):

```bash
sudo docker run --detach \
    --hostname gitlab.example.com \
    --publish 30001:443 --publish 30000:80 --publish 30002:22 \
    --name gitlab \
    --volume /srv/gitlab/config:/etc/gitlab \
    --volume /srv/gitlab/logs:/var/log/gitlab \
    --volume /srv/gitlab/data:/var/opt/gitlab \
    --env GITLAB_ROOT_PASSWORD=password1 \
    gitlab/gitlab-ce:13.10.3-ce.0
```
Gitlab CE only provides docker images for `linux/amd64`, so if host machine is a Mac with Apple's M1 chips, you have to replace `gitlab/gitlab-ce` with `yrzr/gitlab-ce-arm64v8`. `yrzr/gitlab-ce-arm64v8` is compatible with MacOs(M1), but we are not sure whether the performance of the gitlab deployed on MacOs(M1) is consistent with the official one.

Since the authentication is required for *GitLab* (that is, an OAuth2 token should be passed in the  `Authorization` header), run the following command to send an HTTP request to GitLab to ask for a token:

```bash
curl -d 'grant_type=password&username=admin@example.com&password=password1' -X POST http://localhost:30000/oauth/token
```

The response received looks like:

```bash
{
 "access_token": "de6780bc506a0446309bd9362820ba8aed28aa506c71eedbe1c5c4f9dd350e54",
 "token_type": "bearer",
 "expires_in": 7200,
 "refresh_token": "8257e65c97202ed1726cf9571600918f3bffb2544b26e00a61df9897668c33a1",
 "created_at": 1607635748
}
```

The value of `access_token` is the token that is required to test APIs of GitLab. Run the following command for verification (replace `<OAUTH-TOKEN>` with the value of `access_token` received):

```bash
curl --header "Authorization: Bearer <OAUTH-TOKEN>" "http://localhost:30000/api/v4/projects"
```

**Get into the `restct` container again**, and check the connection with the Gitlab service:

```bash
docker run --network host -i -t lxxu/restct:latest /bin/bash
curl -L http://localhost:30000/
```



### 2. Setup Bing Maps

We rely on the publicly hosted service of Bing Maps to perform testing, so there is no need to deploy the service.

However, the authentication is still required. To this end, please register an account at [Bing Maps Dev Center](https://www.bingmapsportal.com/) at first. Then, apply an API key according to the following steps:

- Sign in to the Bing Maps Dev Center with your account.
- Go to “My Account” and click on “My Keys.”
- Fill out the form and click on the “Create” button (leave Key Type and Application Type as their default values)
- In the "Key details" section, click on the "Show Key" link to get the token.



### 3. Run the Experiments

**The commands in this section should be executed inside the `restct` container**.

First, run the following command to generate experiment scripts (replace `<GitLab-TOKEN>` and `<BingMaps-TOKEN>` with their respective tokens received before):

```bash
# for GitLab
python3.8 /root/RestCT/exp/scripts.py --gitlabAuth <GitLab-TOKEN>
# for Bing Maps
python3.8 /root/RestCT/exp/scripts.py --bingMapAuth <BingMaps-TOKEN>
```



#### RQ1

Run the following command to apply RestCT to test subject APIs under the default coverage strength configuration `(ss,es,as) = (2,3,2)` (repeat once for each subject API):

```bash
# test GitLab (6 APIs)
cd /root/RestCT/exp/output/GitLab_RQ1
bash /root/RestCT/exp/runScripts/GitLab_RQ1/runAll.sh 
# test Bing Maps (5 APIs)
cd /root/RestCT/exp/output/BingMap_RQ1
bash /root/RestCT/exp/runScripts/BingMap_RQ1/runAll.sh 
```

**It will take about one hour to test all APIs of GitLab, and three hours to test all APIs of Bing Maps**.

For a quick assessment, we recommend running the experiments on the APIs of **Branch** (for GitLab) and **Elevations** (for Bing Maps), which will take several minutes only to execute (scripts to test each single subject API can be found in the `scripts` directory):

```bash
# test Branch (GitLab)
cd /root/RestCT/exp/output/GitLab_RQ1
bash /root/RestCT/exp/runScripts/GitLab_RQ1/scripts/Branch_2_3_2.sh
# test Elevations (Bing Maps)
cd /root/RestCT/exp/output/BingMap_RQ1
bash /root/RestCT/exp/runScripts/BingMap_RQ1/scripts/Elevations_2_3_2.sh
```

Once the test execution finishes, statistics of test results can be found in the `statistics.csv` file:

```bash
cat statistics.csv
```



#### RQ2

Run the following command to apply RestCT to test subject APIs under six different coverage strength configurations (repeat once for each subject API):

```bash
# test GitLab (6 APIs * 6 configurations)
cd /root/RestCT/exp/output/GitLab_RQ2
bash /root/RestCT/exp/runScripts/GitLab_RQ2/runAll.sh 
# test Bing Maps (5 APIs * 6 configurations)
cd /root/RestCT/exp/output/BingMap_RQ2
bash /root/RestCT/exp/runScripts/BingMap_RQ2/runAll.sh 
```

**It will take about 24 hours to test all APIs of either GitLab or Bing Maps**.

Alternatively, for a quick assessment of the performance of RestCT under a specific coverage strength, run the following scripts:

```bash
# test Branch (GitLab)
cd /root/RestCT/exp/output/GitLab_RQ2
bash /root/RestCT/exp/runScripts/GitLab_RQ2/scripts/Branch_[ss]_[es]_[as].sh
# test Elevations (Bing Maps)
cd /root/RestCT/exp/output/BingMap_RQ2
bash /root/RestCT/exp/runScripts/BingMap_RQ2/scripts/Elevations_[ss]_[es]_[as].sh
```

Here, `[ss]`, `[es]`, and `[as]` indicate the coverage strengths applied for operation sequences, essential input-parameters, and all input-parameters, respectively. All possible choices include `1_3_2`, `3_3_2`, `2_2_2`, `2_4_2`, `2_3_1`, `2_3_3` (a high coverage strength typically indicates a high test execution cost).

**Note**: Do not run the experiment scripts (for either RQ1 or RQ2) in parallel to avoid affecting the experimental results.



### 4. Experimental Results

When the executions of the above scripts finish, the test results can be found in the `/root/RestCT/exp/output/GitLab[BingMap]_RQ1[RQ2]` directory. For each test execution, the results reported include:

* `statistics.csv`: this file records primary metrics for evaluation (that is, the numbers reported in the paper), including:
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



We note that we cannot guarantee a 100% accurate replication of our experiments. As also pointed out by [other studies](https://github.com/EMResearch/EvoMaster/blob/master/docs/replicating_studies.md), the approaches of testing RESTful APIs typically suffer from non-determinism, because they need deal with the networking, and the algorithms usually involve some levels of randomness. In addition, some subject APIs are remotely deployed web services, and they could be updated unpredictably. Hence, after running the above scripts, experimental results that are different from those reported in the paper might be observed (especially, when the testing process is only repeated one or two times). Nevertheless, the average results should be similar in most of the time.
