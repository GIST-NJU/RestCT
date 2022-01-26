# Replication of Experiments

The performance of RestCT is evaluated under 11 real-world subject APIs of two servcie systems, *GitLab* and *Bing Maps* (their Swagger specifications are available in the `spec` directory). This document provides instructions for replicating the above experiments.

For the instructions that use Docker images to replicate the experiments, please see [README_DOCKER](../README_DOCKER.md).



## Test GitLab (6 APIs)

### 1. Service Deployment

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



### 2. Authentication Configuration

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


### 3. Run the Experiments 
**Suppose the abs path of RESTCT is `/root/RestCT`**, run the following command to generate experiment scripts:

```bash
# generate scripts for RQ1
python /root/RestCT/exp/scripts.py \
        --swaggerDir /root/RestCT/exp/swagger/GitLab \
        --expObj GitLab_s2_e3_a2_r5_1h \
        --dir /root/RQ1_GitLab_Output \
        --scriptFolder /root/RQ1_GitLab_Scripts \
        --gitlabAuth <OAUTH-TOKEN> \
        --toolDir /root/RestCT/src/restct.py
```

* Replace `<OAUTH-TOKEN>` with token got above 
* `--expObj GitLab_s2_e3_a2_r5_1h` generate shell scripts for each subject API of *GitLab* with default coverage strengths `2,3,2`(i.e., SStrength=2, EStrength=3, AStrength=2), each API is repeated 5 times for up to 1 hour
* `--dir`: the root directory of testing results produced
* `--scriptFolder`: the root directory of generated scripts
* `--swaggerDir`: the root directory of necessary swagger files
* To generate experiment scripts for RQ2, 
  * replace `--expObj GitLab_s2_e3_a2_r5_1h` with `--expObj GitLab_s1_e3_a2_r5_5h,GitLab_s3_e3_a2_r5_5h,GitLab_s2_e2_a2_r5_5h,GitLab_s2_e4_a2_r5_5h,GitLab_s2_e3_a1_r5_5h,GitLab_s2_e3_a3_r5_5h`. That is, run RestCT with six additional configurations of coverage strengths, including `1,3,2`, `3,3,2`, `2,2,2`, `2,4,2`, `2,3,1`, and `2,3,3`, each API is repeated 5 times for up to 5 hours
  * replace `--dir /root/RQ1_GitLab_Output` with `--dir /root/RQ2_GitLab_Output`
  * replace `--scriptFolder /root/RQ1_GitLab_Scripts` with `--scriptFolder /root/RQ2_GitLab_Scripts`

For RQ1, we run the following command to automated test each API
```bash
cd /root/RQ1_GitLab_Output
nohup bash /root/RQ1_GitLab_Scripts/runAll.sh 2>&1 &
```

For RQ2, we run the following command to automated test each API
```bash
cd /root/RQ2_GitLab_Output
nohup bash /root/RQ2_GitLab_Scripts/runAll.sh 2>&1 &
```

The experiment is not over until the word "Done!" appears in the standard output `./nohup.out`

**The RestCT tool requests the same GitLab server, so the two groups of experiments must not be parallel**

**For RQ1, we commended to use subject `branch`, `commit`,`groups`, or `repository` as a quick assessemnt (about 2~6 minutes for each to execute), because the other two subjects might take about 30 minutes to execute**.

**For RQ2, we commend to use ... as a quick assessemnt, because ...**

Once the test execution finishes, several evaluation metrics will be calculated and recorded. See the end of this document for the interpretation of these results.



## Test BingMaps (5 APIs)

We rely on the publicly hosted service of Bing Maps to perform testing, so there is no need to deploy the service.



## 1. Authentication Configuration

Authentication is also required for *Bing Maps*. To do this, please register an account at [Bing Maps Dev Center](https://www.bingmapsportal.com/) at first.

Then, apply an API key according to the following steps:

- Sign in to the Bing Maps Dev Center with your Microsoft Account.
- Go to “My Account” and click on “My Keys.”
- Fill out the form and click “Create” and get your API key details.



### 2. Run the Experiments (一个或多个 .py 脚本应该都可以)

**Suppose the abs path of RESTCT is `/root/RestCT`**, run the following command to generate experiment scripts:

```bash
# generate scripts for RQ1
python /root/RestCT/exp/scripts.py \
        --swaggerDir /root/RestCT/exp/swagger/BingMap \
        --expObj BingMap_s2_e3_a2_r5_1h \
        --dir /root/RQ1_BingMap_Output \
        --scriptFolder /root/RQ1_BingMap_Scripts \
        --bingMapAuth <KEY-TOKEN> \
        --toolDir /root/RestCT/src/restct.py
```

* Replace `<KEY-TOKEN>` with your API key 

* To generate experiment scripts for RQ2, 
  * replace `--expObj BingMap_s2_e3_a2_r5_1h` with `--expObj BingMap_s1_e3_a2_r5_5h,BingMap_s3_e3_a2_r5_5h,BingMap_s2_e2_a2_r5_5h,BingMap_s2_e4_a2_r5_5h,BingMap_s2_e3_a1_r5_5h,BingMap_s2_e3_a3_r5_5h`. That is, run RestCT with six additional configurations of coverage strengths, including `1,3,2`, `3,3,2`, `2,2,2`, `2,4,2`, `2,3,1`, and `2,3,3`, each API is repeated 5 times for up to 5 hours
  * replace `--dir /root/RQ1_BingMap_Output` with `--dir /root/RQ2_BingMap_Output`
  * replace `--scriptFolder /root/RQ1_BingMap_Scripts` with `--scriptFolder /root/RQ2_BingMap_Scripts`



For RQ1, we run the following command to automated test each API
```bash
cd /root/RQ1_BingMap_Output
nohup bash /root/RQ1_BingMap_Scripts/runAll.sh 2>&1 &
```

For RQ2, we run the following command to automated test each API
```bash
cd /root/RQ2_BingMap_Output
nohup bash /root/RQ2_BingMap_Scripts/runAll.sh 2>&1 &
```

**Do not run the two groups of experiments in parallel**



## Experimental Data

When the execution of RestCT finishes, the test results can be found in the `xxx` direcotry. These include:

* `statistics.csv`: this file records primary metrics for evaluation (tht is, the numbers reported in the paper), including:
  * coverage strengths applied (*SStrength*=2, *EStrength*=3, and *AStrength*=2, by default)
  * the number of operation sequences generated (*Seq*)
  * average length of each operation sequence (*Len*)
  * 1-way and 2-way sequences that are actually tested (*C_1_way* and *C_2_way*)
  * number of all t-way sequences of operations (*All C_SStrength_way*)
  * number of bugs detected (*Bug*)
  * execution time costs, in seconds (*Cost*) 
* `swagger`
  * `acts`: this directory records input and ouput files of the ACTS covering array generator
  * `bug`: this directory records the detailed information of bugs detected
  * `log`: this directory records the stdout obtained during the tool execution
  * `unresolvedParams.json`: this file records the set of unsolved parameters during the tool execution
