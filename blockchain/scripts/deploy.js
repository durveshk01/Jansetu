async function main(){const C=await ethers.getContractFactory('JanSetuAudit');const c=await C.deploy();await c.waitForDeployment();console.log('JanSetuAudit:',await c.getAddress());}
main().catch(e=>{console.error(e);process.exit(1)});
