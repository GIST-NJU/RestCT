# Replication of Experiments

The performance of RestCT is evaluated under 11 real-world subject APIs of two service systems, *GitLab* and *Bing Maps* (their Swagger specifications are available in the `swagger` directory). This document provides instructions for replicating the above experiments in a **Linux** platform.

For the instructions that use Docker images to replicate the experiments, please see [README_DOCKER](https://github.com/GIST-NJU/RestCT/blob/main/README_DOCKER.md).



## Setup the Services Under Test

### 1. GitLab

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



### 2. Bing Maps

We rely on the publicly hosted service of Bing Maps to perform testing, so there is no need to deploy the service. 

However, the authentication is also required. To this end, please register an account at [Bing Maps Dev Center](https://www.bingmapsportal.com/) at first. Then, apply an API key according to the following steps:

- Sign in to the Bing Maps Dev Center with your account.
- Go to “My Account” and click on “My Keys.”
- Fill out the form and click on the “Create” button (leave Key Type and Application Type as their default values)
- In the "Key details" section, click on the "Show Key" link to get the token.



## Run the Experiments

First, set the **abs path** of the RestCT repo:

```bash
export RESTCT_HOME=<abs path of RestCT repo>
```

Next, run the following command to generate experiment scripts (replace `<GitLab-TOKEN>` and `<BingMaps-TOKEN>` with their respective tokens received before):

```bash
# for GitLab
python $RESTCT_HOME/exp/scripts.py --gitlabAuth <GitLab-TOKEN>
# for Bing Maps
python $RESTCT_HOME/exp/scripts.py --bingMapAuth <BingMaps-TOKEN>
```



#### RQ1

Run the following command to apply RestCT to test subject APIs under the default coverage strength configuration `(ss,es,as) = (2,3,2)` (repeat once for each subject API):

```bash
# test GitLab (6 APIs)
cd $RESTCT_HOME/exp/output/GitLab_RQ1
nohup bash $RESTCT_HOME/exp/runScripts/GitLab_RQ1/runAll.sh 2>&1 &
# test Bing Maps (5 APIs)
cd $RESTCT_HOME/exp/output/BingMap_RQ1
nohup bash $RESTCT_HOME/exp/runScripts/BingMap_RQ1/runAll.sh 2>&1 &
```

**It will take about one hour to test all APIs of GitLab, and three hours to test all APIs of Bing Maps**.

For a quick assessment, we recommend running the experiments on the APIs of **Branch** (for GitLab) and **Elevations** (for Bing Maps), which will take several minutes only to execute (scripts to test each single subject API can be found in the `scripts` directory):

```bash
# test Branch (GitLab)
cd $RESTCT_HOME/exp/output/GitLab_RQ1
bash $RESTCT_HOME/exp/runScripts/GitLab_RQ1/scripts/Branch_2_3_2.sh
# test Elevations (Bing Maps)
cd $RESTCT_HOME/exp/output/BingMap_RQ1
bash $RESTCT_HOME/exp/runScripts/BingMap_RQ1/scripts/Elevations_2_3_2.sh
```

Once the test execution finishes, statistics of test results can be found in the `statistics.csv` file:

```bash
cat statistics.csv
```



#### RQ2

Run the following command to apply RestCT to test subject APIs under six different coverage strength configurations (repeat once for each subject API):

```bash
# test GitLab (6 APIs * 6 configurations)
cd $RESTCT_HOME/exp/output/GitLab_RQ2
nohup bash $RESTCT_HOME/exp/runScripts/GitLab_RQ2/runAll.sh 2>&1 &
# test Bing Maps (5 APIs * 6 configurations)
cd $RESTCT_HOME/exp/output/BingMap_RQ2
nohup bash $RESTCT_HOME/exp/runScripts/BingMap_RQ2/runAll.sh 2>&1 &
```

**It will take more than 24 hours to test all APIs of either GitLab or Bing Maps**.

Alternatively, for a quick assessment of the performance of RestCT under a specific coverage strength, run the following scripts:

```bash
# test Branch (GitLab)
cd $RESTCT_HOME/exp/output/GitLab_RQ2
bash $RESTCT_HOME/exp/runScripts/GitLab_RQ2/scripts/Branch_[ss]_[es]_[as].sh 
# test Elevations (Bing Maps)
cd $RESTCT_HOME/exp/output/BingMap_RQ2
bash $RESTCT_HOME/exp/runScripts/BingMap_RQ2/scripts/Elevations_[ss]_[es]_[as].sh 
```

Here, `[ss]`, `[es]`, and `[as]` indicate the coverage strengths applied for operation sequences, essential input-parameters, and all input-parameters, respectively. All possible choices include `1_3_2`, `3_3_2`, `2_2_2`, `2_4_2`, `2_3_1`, `2_3_3` (a high coverage strength typically indicates a high test execution cost).

**Note**: Do not run the experiment scripts (for either RQ1 or RQ2) in parallel to avoid affecting the experimental results.



## Experimental Results

When the executions of the above scripts finish, the test results can be found in the `exp/output` directory. For each test execution, the results reported include:

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

