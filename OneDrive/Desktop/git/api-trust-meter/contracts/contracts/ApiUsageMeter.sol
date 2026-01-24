// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ApiUsageMeter {
    struct Api {
        address owner;
        string name;
        uint256 pricePerRequest;
        bool exists;
    }
    
    struct PaymentBatch {
        address user;
        uint256 apiId;
        uint256 requestCount;
        uint256 totalAmount;
        bool paid;
    }
    
    mapping(uint256 => Api) public apis;
    mapping(bytes32 => PaymentBatch) public paymentBatches;
    uint256 public nextApiId;
    
    event ApiRegistered(uint256 indexed apiId, address indexed owner, string name, uint256 price);
    event PaymentSettled(
        bytes32 indexed batchId,
        address indexed user,
        uint256 indexed apiId,
        uint256 requestCount,
        uint256 totalAmount
    );
    event PaymentReceived(address indexed from, uint256 amount);
    
    function registerApi(string memory _name, uint256 _pricePerRequest) external returns (uint256) {
        uint256 apiId = nextApiId++;
        apis[apiId] = Api({
            owner: msg.sender,
            name: _name,
            pricePerRequest: _pricePerRequest,
            exists: true
        });
        
        emit ApiRegistered(apiId, msg.sender, _name, _pricePerRequest);
        return apiId;
    }
    
    function settlePayment(
        bytes32 _batchId,
        address _user,
        uint256 _apiId,
        uint256 _requestCount
    ) external payable {
        require(apis[_apiId].exists, "API does not exist");
        require(!paymentBatches[_batchId].paid, "Batch already paid");
        
        uint256 totalAmount = _requestCount * apis[_apiId].pricePerRequest;
        require(msg.value >= totalAmount, "Insufficient payment");
        
        paymentBatches[_batchId] = PaymentBatch({
            user: _user,
            apiId: _apiId,
            requestCount: _requestCount,
            totalAmount: totalAmount,
            paid: true
        });
        
        // Transfer to API owner
        payable(apis[_apiId].owner).transfer(totalAmount);
        
        // Refund excess if any
        if (msg.value > totalAmount) {
            payable(msg.sender).transfer(msg.value - totalAmount);
        }
        
        emit PaymentSettled(_batchId, _user, _apiId, _requestCount, totalAmount);
        emit PaymentReceived(_user, totalAmount);
    }
    
    function getApi(uint256 _apiId) external view returns (address owner, string memory name, uint256 price, bool exists) {
        Api memory api = apis[_apiId];
        return (api.owner, api.name, api.pricePerRequest, api.exists);
    }
}