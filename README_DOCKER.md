# Docker Images for Artifact Evaluation

We provide Docker images to simply the assesment of the RestCT tool. In this case, users can skip all prerequisite steps to run the RestCT tool, and also replicate the experiments reported in the paper.



## Setup



## Use RestCT to Test a Demo Service





## Use RestCT to Replicate Experiments

#### 1. Experiments of RQ1

#### 2. Experiments of RQ2



## Additional Notes

We note that we cannot guarantee a 100% accurate replication of our experiments in the artifact. As also pointed out by [previous studies](https://github.com/EMResearch/EvoMaster/blob/master/docs/replicating_ studies.md), the approaches of testing RESTful APIs will deal with the networking (non-determinism often occurs), and the algorithm typically involves some levels of randomness. In addition, some subject APIs are remotely deployed web services, and they could be updated frequently. Hence, after running scripts in the artifact, experimental results that are different from those reported in the paper might be observed (especially, when the testing process is only repeated one or two times). Nevertheless, the average results should be similar in most of the times.
