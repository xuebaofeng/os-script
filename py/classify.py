from subprocess import call

baseDir = "/Users/bxue"

dirs = [baseDir, baseDir + "/Downloads", baseDir + "/Documents"]

types = ["java", "sql", "csv", "apk", "epub", "mobi", "iso", "zip", "rar", "dmg", "pdf", "xlsx", "xml"]

for aDir in dirs:
  for aType in types:
    print(aDir)
    command = ["classifier", "-st", "." + aType, "-sf", "c_" + aType, "-o", baseDir]
    print(" ".join(command))
    call(command, cwd=aDir)
