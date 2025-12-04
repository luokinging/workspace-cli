- Readme 文件调整，readme 中对 workspace 命名不合适，workspace 是一个长期存在的概念，而不是随着 feature 开发结束而结束

  - 提到 workspace create feature-A 是不正确的，应该直接是 workspace create A ，然后得到的是 {base_name}-A

- 请检查 preview 过程精确找到变动的文件的同步是否是通过 git 实现的(先 git add .) 然后通过 git 的命令找到和 workspace 的 common 最近的 提交 root，然后做文件同步
