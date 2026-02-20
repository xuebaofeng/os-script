import subprocess
import winreg

def check_dotnet_runtimes():
    print("=== 检查 .NET Core / .NET 5+ 运行时 ===")
    try:
        result = subprocess.run(["dotnet", "--list-runtimes"], capture_output=True, text=True, check=True)
        if result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                print(line)
        else:
            print("未检测到任何 .NET Core/.NET 5+ 运行时")
    except FileNotFoundError:
        print("未安装 dotnet 命令（.NET Core/.NET 5+ 未安装）")

def check_dotnet_framework():
    print("\n=== 检查 .NET Framework ===")
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full")
        release, _ = winreg.QueryValueEx(key, "Release")
        version = "未知版本"
        if release >= 533325:
            version = "4.8.1+"
        elif release >= 528040:
            version = "4.8"
        elif release >= 461808:
            version = "4.7.2"
        elif release >= 461308:
            version = "4.7.1"
        elif release >= 460798:
            version = "4.7"
        elif release >= 394802:
            version = "4.6.2"
        elif release >= 394254:
            version = "4.6.1"
        elif release >= 393295:
            version = "4.6"
        elif release >= 379893:
            version = "4.5.2"
        elif release >= 378675:
            version = "4.5.1"
        elif release >= 378389:
            version = "4.5"
        print(f".NET Framework 已安装版本: {version}")
    except FileNotFoundError:
        print("未检测到 .NET Framework 4.5+ 安装")

def main():
    check_dotnet_runtimes()
    check_dotnet_framework()
    print("\n=== 建议 ===")
    print("1. 根据应用程序目标安装对应 .NET Runtime 或 Desktop Runtime")
    print("2. 如果运行老程序，确保 .NET Framework 4.8 已安装")
    print("3. 多版本可共存，无需卸载旧版本")

if __name__ == "__main__":
    main()