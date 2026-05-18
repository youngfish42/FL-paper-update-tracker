# DBLP 联邦学习相关检索关键词建议

> 本文档用于补充现有 `federate` 检索词未能覆盖的相关论文。
> 核心原则：**新增检索词与 `federate` 尽量互斥**，即尽量抓取标题不含 `federated` / `federates` / `federating` / `federation` 等词根、但实质属于联邦学习领域的论文。
>
> **验证依据**：基于 README.md 中收录的论文标题逐条核验，仅保留在标题中**确实不含 federate 且属于联邦学习领域**的检索方向。

---

## DBLP 搜索语法速查

| 功能 | 语法 | 示例 | 说明 |
|------|------|------|------|
| 前缀搜索（默认） | 直接输入 | `federate` 匹配 `federated`, `federates`, `federating` | **注意**：前缀不匹配更短的词根，如 `federate` **不匹配** `federal` |
| 精确单词 | 末尾加 `$` | `graph$` 只匹配 `graph`，不匹配 `graphics` | 用于消除歧义 |
| 布尔 AND | 空格分隔 | `client selection` 表示同时包含两者 | 默认连接符 |
| 布尔 OR | `\|` 分隔 | `split\|swarm` 表示包含任一 | 用于扩展同义词 |

> ⚠️ 短语搜索运算符 (`.`) 已禁用；布尔 NOT 运算符 (`-`) 已禁用。

### 语法陷阱：AND / OR 优先级

DBLP 中 **`\|` 的优先级高于空格（AND）**，且**不支持括号**改变优先级。

- ❌ 错误写法：`collaborative|communication learning`  
  实际解析为：`collaborative* OR (communication* AND learning*)`  
  会返回所有含 "collaborative" 的论文（无论是否含 learning），噪声巨大。

- ✅ 正确写法：`collaborative learning|communication efficient learning`  
  实际解析为：`(collaborative* AND learning*) OR (communication* AND efficient* AND learning*)`  
  这才是我们想要的语义。

**结论**：当多个 AND 组合需要用 `\|` 连接时，必须把公共部分重复写出，不能省略。

---

## 与 `federate` 互斥的检索词

### 一、高互斥度核心推荐（强烈推荐）

以下方向的论文标题**经 README.md 逐条核验**，确认存在多篇标题不含 `federate` 词根、但实质属于联邦学习领域的论文。

#### 1. Gradient Inversion（梯度反演）

梯度反演攻击是联邦学习隐私安全的重要研究方向。大量论文标题只提 `gradient inversion`，不含 `federate`。

| 检索词 | DBLP 语法 | README 中不含 federate 的实例 |
|--------|-----------|------------------------------|
| 梯度反演 | `gradient inversion` | *Gradient Inversion of Multimodal Models*, *Exploring User-level Gradient Inversion with a Diffusion Prior*, *Towards Eliminating Hard Label Constraints in Gradient Inversion Attacks* |

**检索式：**
```text
gradient inversion
```

#### 2. FedAvg（联邦平均算法）

FedAvg 是联邦学习最经典的算法。多篇理论分析论文标题直接使用 `FedAvg` 而不含 `federate`。

| 检索词 | DBLP 语法 | README 中不含 federate 的实例 |
|--------|-----------|------------------------------|
| 联邦平均 | `FedAvg` | *Widening the Network Mitigates the Impact of Data Heterogeneity on FedAvg*, *FedAvg Converges to Zero Training Loss Linearly...*, *On the Convergence of FedAvg on Non-IID Data* |

**检索式：**
```text
FedAvg
```

> 说明：`FedAvg` 为 FL 领域专用算法名，DBLP 中几乎只匹配联邦学习相关论文，噪声极低。前缀搜索同时覆盖 `FedAvgM` 等变体。

#### 3. FedProx（联邦近端算法）

FedProx 是联邦学习另一经典算法（处理异构数据的 FedAvg 扩展）。部分理论分析论文标题使用 `FedProx` 而不含 `federate`。

| 检索词 | DBLP 语法 | README 中不含 federate 的实例 |
|--------|-----------|------------------------------|
| 联邦近端 | `FedProx` | *On Convergence of FedProx: Local Dissimilarity Invariant Bounds, Non-smoothness and Beyond* |

**检索式：**
```text
FedProx
```

> 说明：`FedProx` 为 FL 领域专用算法名，噪声极低。

#### 4. Collaborative Learning（协作学习）

协作学习与联邦学习概念高度重叠。多篇论文标题使用 `collaborative learning` 而不含 `federate`。

| 检索词 | DBLP 语法 | README 中不含 federate 的实例 |
|--------|-----------|------------------------------|
| 协作学习 | `collaborative learning` | *CoBo: Collaborative Learning via Bilevel Optimization*, *Fair yet Asymptotically Equal Collaborative Learning*, *Adversarial Collaborative Learning on Non-IID Features* |
| 协作机器学习 | `collaborative machine learning` | *Gradient Driven Rewards to Guarantee Fairness in Collaborative Machine Learning* |

**检索式（建议拆分为两次独立查询）：**
```text
collaborative learning
collaborative machine learning
```

> ⚠️ **注意**：`collaborative learning|collaborative machine learning` 是两个低频双字词组，用 `\|` 连接可能丢失结果。建议拆分为独立查询。

#### 5. Local SGD（本地 SGD）

Local SGD（又称 Federated Averaging / FedAvg）是联邦学习的核心算法之一。部分理论分析论文标题使用 `local SGD` 而不提 `federated`。

| 检索词 | DBLP 语法 | README 中不含 federate 的实例 |
|--------|-----------|------------------------------|
| 本地 SGD | `local SGD` | *Learning Optimizers for Local SGD*, *Global Convergence Analysis of Local SGD for Two-layer Neural Network...*, *Minibatch vs Local SGD with Shuffling* |

**检索式：**
```text
local SGD
```

#### 6. Communication-Efficient Distributed（通信高效分布式）

通信效率是联邦学习的核心优化目标。部分分布式学习论文标题使用 `communication-efficient distributed` 而不含 `federated`。

| 检索词 | DBLP 语法 | README 中不含 federate 的实例 |
|--------|-----------|------------------------------|
| 通信高效分布式 | `communication-efficient distributed` | *LoCoDL: Communication-Efficient Distributed Learning with Local Training and Compression*, *Client Sampling for Communication-Efficient Distributed Minimax Optimization* |

**检索式：**
```text
communication-efficient distributed
```

#### 7. Model Merging（模型合并）

模型合并是联邦学习模型聚合的重要技术方向。部分论文标题使用 `model merging` 而不提 `federated`。

| 检索词 | DBLP 语法 | README 中不含 federate 的实例 |
|--------|-----------|------------------------------|
| 模型合并 | `model merging` | *MAP: Model Merging with Amortized Pareto Front Using Limited Computation*, *TIES-Merging: Resolving Interference When Merging Models* |

**检索式：**
```text
model merging
```

---

### 二、补充推荐（互斥性高但样本较少）

#### 8. Swarm Learning（群体学习）

Swarm Learning 是 HP 实验室提出的去中心化机器学习框架，Nature 正刊论文推广。该领域论文标题**完全不用** `federate`，是联邦学习在医疗数据隐私保护场景的重要平行方向。README 中收录样本较少，但互斥性极高。

| 检索词 | DBLP 语法 | README 中不含 federate 的实例 |
|--------|-----------|------------------------------|
| 群体学习 | `swarm learning` | *Swarm Learning for decentralized and confidential clinical machine learning* (Nature 2021) |

**检索式：**
```text
swarm learning
```

---

### 三、已删除的检索词（说明）

以下检索词在初版文档中曾出现，但经 README.md 标题核验后删除，原因如下：

| 删除的检索词 | 删除原因 |
|-------------|---------|
| `secure aggregation` | 互斥性极低：README 中几乎所有实例标题同时含 `federated` |
| `client selection` | 互斥性极低：README 中几乎所有实例标题同时含 `federated` |
| `cross-silo` / `cross-device` | 互斥性极低：README 中几乎所有实例标题同时含 `federated` |
| `model poisoning` | 互斥性极低：README 中几乎所有实例标题同时含 `federated` |
| `split learning` | 互斥性极低：README 中绝大多数为 "Split Federated Learning"，同时含 `federated` |
| `gradient compression` | 互斥性低，且与 `communication-efficient` 覆盖范围重叠 |
| `decentralized learning` | 过度发散：会引入大量 gossip-based optimization、decentralized VI 等非联邦学习论文 |
| `edge intelligence` / `edge learning` | 过度发散：边缘计算领域远大于联邦学习，README 中几乎无不含 federate 的联邦学习实例 |
| `privacy-preserving machine learning` | 过度发散：领域过宽，大量非联邦学习论文 |
| `distributed knowledge distillation` | 过度发散：README 中无不含 federate 的联邦学习实例 |
| `model averaging` | 过度发散：README 中实例多为参数平均/多任务学习，非联邦学习特指 |
| `data silo` | 无实例支撑：README 中几乎无相关论文 |

---

## ⚠️ 为什么不能简写？一个具体例子

以协作学习检索式为例：

| 写法 | DBLP 实际解析 | 语义 | 是否可用 |
|------|--------------|------|---------|
| `collaborative learning|collaborative machine learning` | `(collaborative* AND learning*) OR (collaborative* AND machine* AND learning*)` | 两组 AND 的并集 | ✅ |
| `collaborative|machine learning` | `collaborative* OR (machine* AND learning*)` | 含 collaborative 或 machine learning 的论文都会返回 | ❌ |

第二种写法会引入大量只含 "collaborative" 但无关的论文，因此**不可省略重复词**。

---

## 可直接使用的 DBLP 查询字符串

### 分主题检索（推荐，低噪声）

复制以下表达式直接粘贴到 DBLP 搜索框即可：

| 主题 | DBLP 查询字符串 |
|------|----------------|
| 🔓 梯度反演 | `gradient inversion` |
| ⚖️ 联邦平均 | `FedAvg` |
| 🔗 联邦近端 | `FedProx` |
| 🤝 协作学习 | `collaborative learning` |
| 📍 本地 SGD | `local SGD` |
| 📡 通信高效分布式 | `communication-efficient distributed` |
| 🔗 模型合并 | `model merging` |
| 🐝 群体学习 | `swarm learning` |

---

## 多组互补检索式（API 调用推荐）

> 由于 DBLP API 对单个查询的长度和复杂度存在限制（URL 长度、解析深度等），**不建议将所有检索词堆砌为单个查询**。建议按以下多组分次调用 API，最后合并去重。

### 分组原则

- **组内同质**：每组聚焦一个技术方向。
- **组间互补**：各组之间无重叠覆盖，合起来覆盖全部互斥方向。
- **低频拆分**：对于低频双字词组，拆分为独立查询。
- **有据可依**：每组均经 README.md 标题核验，确认存在不含 `federate` 的联邦学习论文。

### 核心推荐分组（共 8 个方向，9 次查询）

| 组号 | 技术方向 | DBLP 查询字符串 | 说明 |
|------|---------|----------------|------|
| **G1** | 梯度反演 | `gradient inversion` | 隐私攻击方向，多篇不含 federate 的实例 |
| **G2** | 联邦平均 | `FedAvg` | FL 核心算法名，噪声极低 |
| **G3** | 联邦近端 | `FedProx` | FL 核心算法名，噪声极低 |
| **G4** | 协作学习 | `collaborative learning` | 协作学习方向，多篇不含 federate 的实例 |
| **G5** | 本地 SGD | `local SGD` | 联邦学习核心算法，多篇不含 federate 的实例 |
| **G6** | 通信高效分布式 | `communication-efficient distributed` | 通信优化方向，有不含 federate 的实例 |
| **G7** | 模型合并 | `model merging` | 模型聚合方向，有不含 federate 的实例 |
| **G8** | 群体学习 | `swarm learning` | 平行范式，互斥性极高但样本较少 |

> **分组说明**：所有低频双字词组均已独立查询，避免 `\|` 组合导致结果丢失。单字词（如 `FedAvg`）和专用术语（如 `swarm learning`）独立查询最安全。

### 与 venue 过滤结合的分组示例

如果只需要特定会议的论文，可在每组后追加 venue 过滤器：

| 目标 | 查询示例 |
|------|---------|
| NeurIPS 梯度反演 | `gradient inversion venue:NeurIPS:` |
| ICML 联邦平均 | `FedAvg venue:ICML:` |
| ICLR 协作学习 | `collaborative learning venue:ICLR:` |
| ICML 本地 SGD | `local SGD venue:ICML:` |

### 综合检索式（仅作参考，不推荐用于 API）

如果你坚持单次查询，可使用以下完整表达式（长度较长，可能受 API 限制）：

```text
gradient inversion|FedAvg|FedProx|collaborative learning|local SGD|communication-efficient distributed|model merging|swarm learning
```

> ⚠️ 综合式噪声较高且可能触发长度限制，**强烈建议使用上方 G1-G9 分组方案**。特别注意：`collaborative learning|collaborative machine learning` 等低频双字词组组合在综合式中可能严重丢失结果。

---

## DBLP 已知限制（IR 领域实测经验迁移）

### 限制 1：低频双字词组的 `\|` 组合严重丢失结果

**现象**：当使用 `\|` 连接多个分支，且分支为**低频双字词组**（每个分支内部包含空格 AND）时，DBLP 会**严重丢失结果**，甚至返回 **0 结果**。

**IR 领域实测验证**：

| 查询 | 返回结果数 | 状态 |
|------|-----------|------|
| `atlas construction|motion correction|deformation field` | **0** | ❌ |
| `atlas construction|motion correction` | **2**（理论并集 800+） | ❌ |
| `ICP|iterative closest venue:CVPR:` | **0** | ❌ |
| `ICP venue:CVPR:` | 7 | ✅ |

**本文档涉及的风险点**：

| 风险组合 | 风险等级 | 本文档处理方式 |
|---------|---------|--------------|
| `collaborative learning|collaborative machine learning` | 🟡 中等 | **已拆分为 G4/G5 两次独立查询** |
| 其他单字词或独立查询 | 🟢 低 | 全部独立查询，无风险 |

**规律总结**：
- ❌ `A B|C D|E F`（三个低频双字词组）→ 可能返回 0
- 🟡 `A B|C D`（两个低频双字词组）→ venue 过滤后可能严重丢失
- ✅ 单字词查询（如 `FedAvg`）→ 最安全
- ✅ 单分支查询 → 最安全

**结论**：本文档所有低频双字词组均已拆分为独立 API 调用，最大限度避免结果丢失。

---

## 与 venue 过滤结合使用

你可以将上述检索词与 DBLP 的 venue/type 过滤器结合，精确锁定目标会议/期刊。

| 目标 | DBLP 查询字符串示例 |
|------|---------------------|
| NeurIPS 梯度反演 | `gradient inversion venue:NeurIPS:` |
| ICML 联邦平均 | `FedAvg venue:ICML:` |
| ICLR 联邦近端 | `FedProx venue:ICLR:` |
| ICML 本地 SGD | `local SGD venue:ICML:` |
| ICLR 模型合并 | `model merging venue:ICLR:` |

> venue 和 type 过滤器的写法可参考 README 中已有的 DBLP 链接格式。

---

## 互斥性验证方法

你可以快速验证新增检索词与 `federate` 的互斥程度：

1. 搜索 `federate`，记录结果数 **N1**
2. 搜索新增词（如 `gradient inversion`），记录结果数 **N2**
3. 搜索交集 `federate gradient inversion`，记录结果数 **N3**
4. **新增独有率 ≈ (N2 - N3) / N2**，该值越高说明互斥性越强

### 本文档检索词互斥性评级（基于 README.md 标题核验）

| 检索词 | 互斥性评级 | 依据 |
|--------|-----------|------|
| `gradient inversion` | ⭐⭐⭐⭐⭐ 极高 | README 中多篇实例标题不含 federate，噪声低 |
| `FedAvg` | ⭐⭐⭐⭐⭐ 极高 | FL 专用算法名，README 中多篇实例标题不含 federate，噪声极低 |
| `FedProx` | ⭐⭐⭐⭐⭐ 极高 | FL 专用算法名，噪声极低 |
| `collaborative learning` | ⭐⭐⭐⭐ 高 | README 中多篇实例标题不含 federate，有一定噪声 |
| `local SGD` | ⭐⭐⭐⭐ 高 | README 中多篇实例标题不含 federate，噪声较低 |
| `communication-efficient distributed` | ⭐⭐⭐⭐ 高 | README 中有实例标题不含 federate，有一定噪声 |
| `model merging` | ⭐⭐⭐ 中高 | README 中有实例标题不含 federate，噪声较低 |
| `swarm learning` | ⭐⭐⭐⭐⭐ 极高 | 专用术语，完全不用 federate，但样本较少 |

---

## 附：关于 `federate` 前缀覆盖范围的补充说明

DBLP 的默认搜索是**前缀匹配**，这意味着：

- `federate` 匹配：`federate`, `federated`, `federates`, `federating`, `federation`
- `federate` **不匹配**：`federal`, `federative`, `federacy`

如果你的目标是**最大化覆盖**所有联邦学习相关论文，建议在现有 `federate` 的基础上，确认是否需要补充 `federal` 的排除（通常不需要，因为 `federal` 主要指联邦制/联邦政府，与机器学习无关）。

> 但本文档的核心目标是**与 `federate` 互斥的新增检索词**，因此上述补充不在主要推荐之列，仅作备注。
