// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
contract JanSetuAudit {
    address public owner;
    mapping(address => bool) public authorized;
    struct Entry { bytes32 complaintRef; bytes32 eventType; bytes32 eventHash; uint64 timestamp; address actor; }
    Entry[] private entries;
    event AuditRecorded(uint256 indexed id, bytes32 indexed complaintRef, bytes32 eventType, bytes32 eventHash, uint64 timestamp, address actor);
    constructor() { owner = msg.sender; authorized[msg.sender] = true; }
    modifier onlyOwner() { require(msg.sender == owner, "owner only"); _; }
    modifier onlyAuthorized() { require(authorized[msg.sender], "unauthorized"); _; }
    function setAuthorized(address actor, bool enabled) external onlyOwner { authorized[actor] = enabled; }
    function record(bytes32 complaintRef, bytes32 eventType, bytes32 eventHash) external onlyAuthorized returns (uint256 id) {
        id = entries.length; entries.push(Entry(complaintRef,eventType,eventHash,uint64(block.timestamp),msg.sender));
        emit AuditRecorded(id,complaintRef,eventType,eventHash,uint64(block.timestamp),msg.sender);
    }
    function getEntry(uint256 id) external view returns (Entry memory) { require(id < entries.length, "missing"); return entries[id]; }
    function count() external view returns (uint256) { return entries.length; }
}
