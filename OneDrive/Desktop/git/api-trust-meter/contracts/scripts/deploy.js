const hre = require("hardhat");

async function main() {
  const ApiUsageMeter = await hre.ethers.getContractFactory("ApiUsageMeter");
  const apiUsageMeter = await ApiUsageMeter.deploy();
  
  await apiUsageMeter.waitForDeployment();
  
  const address = await apiUsageMeter.getAddress();
  console.log("ApiUsageMeter deployed to:", address);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });