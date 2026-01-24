import React, { useState, useEffect } from 'react'
import { createConfig, WagmiProvider, useAccount, useConnect, useDisconnect, useSignMessage } from 'wagmi'
import { metaMask } from 'wagmi/connectors'
import { http } from 'viem'
import { hardhat } from 'viem/chains'

// Wagmi configuration for local Hardhat
const config = createConfig({
  chains: [hardhat],
  transports: {
    [hardhat.id]: http('http://127.0.0.1:8545'),
  },
  connectors: [metaMask()],
})

// Backend API base URL
const API_BASE_URL = 'http://localhost:8000'

function AppContent() {
  const { address, isConnected } = useAccount()
  const { connect } = useConnect()
  const { disconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()
  
  const [apis, setApis] = useState([])
  const [myApis, setMyApis] = useState([])
  const [selectedApi, setSelectedApi] = useState('')
  const [apiName, setApiName] = useState('')
  const [apiPrice, setApiPrice] = useState('')
  const [usageData, setUsageData] = useState({})
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState({ type: '', text: '' })
  const [authSignature, setAuthSignature] = useState('')

  // Authenticate with backend
  const authenticate = async () => {
    if (!address) return
    
    try {
      // Get nonce from backend
      const nonceRes = await fetch(`${API_BASE_URL}/api/nonce?wallet_address=${address}`)
      const nonceData = await nonceRes.json()
      
      // Create SIWE message
      const message = `${address} wants to sign in with Ethereum.\n\nNonce: ${nonceData.nonce}`
      
      // Sign message
      const signature = await signMessageAsync({ message })
      setAuthSignature(signature)
      
      setMessage({ type: 'success', text: 'Authenticated successfully!' })
    } catch (error) {
      setMessage({ type: 'error', text: `Authentication failed: ${error.message}` })
    }
  }

  useEffect(() => {
    if (isConnected && address) {
      authenticate()
      fetchAvailableApis()
      fetchMyApis()
    }
  }, [isConnected, address])

  const fetchAvailableApis = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/available-apis`, {
        headers: {
          'Wallet-Address': address,
          'Signature': authSignature
        }
      })
      const data = await response.json()
      setApis(data)
    } catch (error) {
      console.error('Error fetching APIs:', error)
    }
  }

  const fetchMyApis = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/my-apis`, {
        headers: {
          'Wallet-Address': address,
          'Signature': authSignature
        }
      })
      const data = await response.json()
      setMyApis(data)
    } catch (error) {
      console.error('Error fetching my APIs:', error)
    }
  }

  const registerApi = async (e) => {
    e.preventDefault()
    if (!apiName || !apiPrice) {
      setMessage({ type: 'error', text: 'Please fill all fields' })
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/register?api_name=${encodeURIComponent(apiName)}&price_per_request=${apiPrice}`, {
        method: 'POST',
        headers: {
          'Wallet-Address': address,
          'Signature': authSignature
        }
      })
      
      if (response.ok) {
        setMessage({ type: 'success', text: 'API registered successfully!' })
        setApiName('')
        setApiPrice('')
        fetchMyApis()
        fetchAvailableApis()
      } else {
        throw new Error('Registration failed')
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Registration failed: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }

  const callApi = async () => {
    if (!selectedApi) {
      setMessage({ type: 'error', text: 'Please select an API' })
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/log-usage?api_id=${selectedApi}`, {
        method: 'POST',
        headers: {
          'Wallet-Address': address,
          'Signature': authSignature
        }
      })
      
      const data = await response.json()
      setUsageData(data)
      setMessage({ type: 'success', text: 'API called successfully!' })
      
      // Fetch updated usage
      fetchApiUsage(selectedApi)
    } catch (error) {
      setMessage({ type: 'error', text: `API call failed: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }

  const fetchApiUsage = async (apiId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/usage/${apiId}`, {
        headers: {
          'Wallet-Address': address,
          'Signature': authSignature
        }
      })
      const data = await response.json()
      setUsageData(data)
    } catch (error) {
      console.error('Error fetching usage:', error)
    }
  }

  const settlePayment = async (apiId) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/settle/${apiId}`, {
        method: 'POST',
        headers: {
          'Wallet-Address': address,
          'Signature': authSignature
        }
      })
      
      const data = await response.json()
      setMessage({ 
        type: 'success', 
        text: 'Settlement prepared! Check console for blockchain transaction data.' 
      })
      console.log('Settlement data:', data.settlement_data)
      
      // In a real app, you would send the transaction to blockchain here
      // For this demo, we'll just mark as settled
      const confirmRes = await fetch(`${API_BASE_URL}/api/confirm-settlement/${apiId}?transaction_hash=mock_tx_hash`, {
        method: 'POST',
        headers: {
          'Wallet-Address': address,
          'Signature': authSignature
        }
      })
      
      if (confirmRes.ok) {
        setMessage({ type: 'success', text: 'Payment settled successfully!' })
        fetchApiUsage(apiId)
        fetchMyApis()
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Settlement failed: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedApi) {
      fetchApiUsage(selectedApi)
    }
  }, [selectedApi])

  return (
    <div className="app">
      <div className="container">
        <div className="header">
          <h1>🔗 Decentralized API Trust Meter</h1>
          <p>Track and pay for API usage on the blockchain</p>
        </div>

        {message.text && (
          <div className={`alert alert-${message.type}`}>
            {message.text}
          </div>
        )}

        <div className="wallet-section">
          <div className="wallet-info">
            {isConnected ? (
              <>
                <span>Connected: </span>
                <div className="wallet-address">{address}</div>
                <button onClick={disconnect} className="btn btn-danger btn-small">
                  Disconnect
                </button>
              </>
            ) : (
              <button onClick={() => connect()} className="btn">
                Connect MetaMask
              </button>
            )}
          </div>
          {isConnected && authSignature && (
            <div className="authentication-status">
              <span style={{ color: '#48bb78', fontWeight: 'bold' }}>✓ Authenticated</span>
            </div>
          )}
        </div>

        {isConnected ? (
          <div className="grid">
            <div className="card">
              <h2>Register New API</h2>
              <form onSubmit={registerApi}>
                <div className="form-group">
                  <label>API Name</label>
                  <input
                    type="text"
                    className="form-control"
                    value={apiName}
                    onChange={(e) => setApiName(e.target.value)}
                    placeholder="My Weather API"
                  />
                </div>
                <div className="form-group">
                  <label>Price per Request (wei)</label>
                  <input
                    type="number"
                    className="form-control"
                    value={apiPrice}
                    onChange={(e) => setApiPrice(e.target.value)}
                    placeholder="1000000000000000"
                    min="0"
                  />
                  <small>1 ETH = 10^18 wei</small>
                </div>
                <button type="submit" className="btn" disabled={loading}>
                  {loading ? 'Registering...' : 'Register API'}
                </button>
              </form>
            </div>

            <div className="card">
              <h2>Call API</h2>
              <div className="form-group">
                <label>Select API to Call</label>
                <select
                  className="form-control"
                  value={selectedApi}
                  onChange={(e) => setSelectedApi(e.target.value)}
                >
                  <option value="">Select an API</option>
                  {apis.map(api => (
                    <option key={api.id} value={api.id}>
                      {api.name} - {api.price} wei/request
                    </option>
                  ))}
                </select>
              </div>
              <button onClick={callApi} className="btn" disabled={!selectedApi || loading}>
                {loading ? 'Calling...' : 'Call API'}
              </button>

              {usageData.request_count > 0 && (
                <div className="usage-info">
                  <h3>Usage Summary</h3>
                  <p>Requests: {usageData.request_count}</p>
                  <p>Pending Payment: {usageData.pending_payment} wei</p>
                  <p>Total Cost: {usageData.total_cost} wei</p>
                  <button 
                    onClick={() => settlePayment(selectedApi)} 
                    className="btn btn-secondary"
                    style={{ marginTop: '15px' }}
                  >
                    Settle Payment
                  </button>
                </div>
              )}
            </div>

            <div className="card">
              <h2>My APIs</h2>
              {myApis.length > 0 ? (
                <ul className="api-list">
                  {myApis.map(api => (
                    <li key={api.id} className="api-item">
                      <h4>{api.name}</h4>
                      <p>Price: {api.price} wei per request</p>
                      <small>API ID: {api.id}</small>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No APIs registered yet.</p>
              )}
            </div>

            <div className="card">
              <h2>Available APIs</h2>
              {apis.length > 0 ? (
                <ul className="api-list">
                  {apis.map(api => (
                    <li key={api.id} className="api-item">
                      <h4>{api.name}</h4>
                      <p>Price: {api.price} wei per request</p>
                      <button 
                        onClick={() => setSelectedApi(api.id)}
                        className="btn btn-small"
                        style={{ marginTop: '10px' }}
                      >
                        Select
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No APIs available.</p>
              )}
            </div>
          </div>
        ) : (
          <div className="card">
            <h2>Welcome!</h2>
            <p>Please connect your MetaMask wallet to get started.</p>
            <p>Make sure you're connected to the local Hardhat network (Chain ID: 31337).</p>
          </div>
        )}
      </div>
    </div>
  )
}

function App() {
  return (
    <WagmiProvider config={config}>
      <AppContent />
    </WagmiProvider>
  )
}

export default App