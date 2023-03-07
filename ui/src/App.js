import React from 'react';
import axios from 'axios';
import ClipLoader from "react-spinners/ClipLoader";
import { BsSearch } from "react-icons/bs";

import './App.css';


class App extends React.Component {

  constructor() {
    super();
    this.state = {query: "Who is Harry Potter?", answers: [], isLoading: false};
  }


  render() {
    return (
      <div className="bg-[#a5a5a5d1] w-screen h-screen flex">
        <div className='absolute'>
          <button onClick={this.startIndex} className='bg-[#886fda] ml-3 text-white p-2 rounded border-2 border-white-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out m-2'>
                Index
          </button>
        </div>
        <div className='mx-auto my-40'>
          <h1 className='text-7xl text-center m-10'>gerev.ai 🧦</h1>
          <div className='flex flex-col container text-3xl p-4 rounded bg-[#ddddddd1] text-white border-2
                         border-slate-700'>
            <div className='flex'>
              {this.state.answers.length > 0 &&
              <a onClick={this.clear} className='text-black mr-2 p-2 cursor-pointer  hover:text-white transition'> 
                X
              </a>
              }
              <input type="text" className='w-full p-2 rounded bg-[#ddddddd1] text-black border-2 border-slate-700'
                     placeholder='Search' value={this.state.query} onChange={this.handleChange} onKeyDown={this.onKeyDown} />
              <button onClick={this.search} className='bg-[#060117] ml-3 text-white p-2 rounded border-2 border-slate-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out flex items-center'>
                <span className='text-3xl mr-2'>Search</span>
                {this.state.isLoading ?
                <ClipLoader
                  color="#ffffff"
                  loading={this.state.isLoading}
                  size={30}
                  aria-label="Loading Spinner"
                /> : <BsSearch></BsSearch>}
              </button>
            </div>

          </div>
        </div>
      </div>
    );  
  }

  startIndex = () => {
    try {
        const response = axios.post("http://localhost:8000/example-index").then(response => {});
    } catch (error) {
      console.error(error);
    }
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
    this.setState({isLoading: true});
    try {
        const response = axios.get("http://localhost:8000/search?query=" + this.state.query).then(response => {
          const answers = response.data.map((answer) => answer.content);
          this.setState({answers: answers, isLoading: false});
        });
    } catch (error) {
      console.error(error);
    }
  };
  
}


export default App;
