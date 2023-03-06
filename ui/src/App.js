import React from 'react';
import axios from 'axios';

import './App.css';


class App extends React.Component {

  constructor() {
    super();
    this.state = {query: "", answers: []};
  }


  render() {
    return (
      <div className="bg-[#a5a5a5d1] w-screen h-screen flex">
        <div className='mx-auto my-auto'>
          <div className='flex flex-col container w-50 text-3xl p-4 rounded bg-[#ddddddd1] text-white border-2 border-slate-700'>
            <div className='flex'>
              {this.state.answers.length > 0 &&
              <a onClick={this.clear} className='text-black mr-2 p-2 cursor-pointer  hover:text-white transition'> 
                X
              </a>
              }
              <input type="text" className='w-full p-2 rounded bg-[#ddddddd1] text-black border-2 border-slate-700'
                     placeholder='Search' value={this.state.query} onChange={this.handleChange} onKeyDown={this.onKeyDown} />
              <button onClick={this.search} className='bg-[#060117] ml-3 text-white p-2 rounded border-2 border-slate-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out'>
                Search
              </button>
            </div>
            {/*Answers for each answer in state */}
            <div className='w-full mt-4'>
              {this.state.answers.map((answer, index) => {
                return (
                  <div key={index} className='p-2 text-black rounded border-2 border-slate-700 mt-2'>
                    {answer}
                  </div>)
              })}
            </div>

          </div>
        </div>
      </div>
    );  
  }

  onKeyDown = (event) => {
    if (event.key === 'Enter') {
      this.search();
    }
  }

  handleChange = (event) => {
    this.setState({query: event.target.value});
  }

  clear = () => {
    this.setState({answers: [], query: ""});
  }

  search = () => {
    console.log(this.state.query)
    this.setState({answers: ["test", "test2"]});
  //   const fetchData = async () => {
  //     try {
  //       const response = await axios.post("http://localhost:80/api/v1/search/", {
  //         "search": "test"
  //       });
  //       console.log(response.data);
  //     } catch (error) {
  //       console.error(error);
  //     }
  //   };
  }
}


export default App;
