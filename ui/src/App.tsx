import * as React from "react";

import axios from 'axios';

import EnterImage from './assets/images/enter.svg';
import { GiSocks } from "react-icons/gi";

import './assets/css/App.css';
import SearchBar from "./components/search-bar";
import { SearchResult, SearchResultProps } from "./components/search-result";
import { addToSearchHistory } from "./autocomplete";

export interface AppState {
  query: string
  results: SearchResultProps[]
  searchDuration: number
  isLoading: boolean
  isNoResults: boolean
}

const api = axios.create({
  baseURL: `http://${window.location.hostname}:8000`,
})

export default class App extends React.Component <{}, AppState>{

  constructor() {
    super({});
    this.state = {
      isLoading: false,
      isNoResults: false,
      query: "",
      results: [],
      searchDuration: 0
    }
  }


  render() {
    return (
      <div className="w-[98vw]">
        <div className='absolute'>
          <button onClick={this.startIndex} className='bg-[#886fda] ml-3 text-white p-2 rounded border-2 border-white-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out m-2'>
                Index
          </button>
        </div>

        {/* front search page*/}
        {
          this.state.results.length === 0 &&    
            <div className='relative flex flex-col items-center top-40 mx-auto w-full'>
                <h1 className='flex flex-row items-center text-7xl text-center text-white m-10'>                
                  <GiSocks className='text-7xl text-center text-[#A78BF6] mt-4 mr-7'></GiSocks>
                  <span className="text-transparent	block font-source-sans-pro md:leading-normal bg-clip-text bg-gradient-to-l from-[#FFFFFF_24.72%] via-[#B8ADFF_50.45%] to-[#B8ADFF_74.45%]">
                    gerev.ai
                  </span>
                </h1>
                <SearchBar query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                          onSearch={this.search} onQueryChange={this.handleQueryChange} onClear={this.clear} showSuggestions={true} />

                <button onClick={this.search} className="h-9 w-28 mt-8 p-3 flex items-center justify-center hover:shadow-sm
                  transition duration-150 ease-in-out hover:shadow-[#6c6c6c] bg-[#2A2A2A] rounded border-[.5px] border-[#6e6e6e88]">
                  <span className="font-bold text-[15px] text-[#B3B3B3]">Search</span>
                  <img className="ml-2" src={EnterImage}></img>
                </button>
                { this.state.isNoResults && 
                  <span className="text-[#D2D2D2] font-poppins font-medium text-base leading-[22px] mt-3">
                  </span>
                }
            </div>  
        } 

        {/* results page */}
        {
          this.state.results.length > 0 && 
          <div className="relative flex flex-row top-20 left-5 w-full">
            <span className='flex flex-row items-start text-3xl text-center text-white m-10 mx-7 mt-0'>
              <GiSocks className='text-4xl text-[#A78BF6] mx-3 my-1'></GiSocks>
              <span className="text-transparent	block font-source-sans-pro md:leading-normal bg-clip-text bg-gradient-to-l from-[#FFFFFF_24.72%] to-[#B8ADFF_74.45%]">gerev.ai</span>
            </span>
            <div className="flex flex-col items-start w-10/12">
              <SearchBar query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                        onSearch={this.search} onQueryChange={this.handleQueryChange} onClear={this.clear} showSuggestions={false} />
              <span className="text-[#D2D2D2] font-poppins font-medium text-base leading-[22px] mt-3">
                {this.state.results.length} Results ({this.state.searchDuration} seconds)
              </span>
              <div className='w-6/12 mt-4 divide-y divide-[#3B3B3B] divide-y-[0.7px]'>
                {this.state.results.map((result, index) => {
                    return (
                      <SearchResult key={index} {...result} />
                      )
                    }
                  )}
              </div>
            </div>
          </div>
        }


      </div>
      
    );  
  }

  startIndex = () => {
    try {
        const response = api.post(`/index-confluence`).then(response => {});
    } catch (error) {
      console.error(error);
    }
  }

  handleQueryChange = (query: string) => {
    this.setState({query: query});
  }
  
  clear = () => {
    this.setState({query: "", results: []});
  }

  search = () => {
    if (this.state.query == "") {
      return;
    }

    this.setState({isLoading: true});
    let start = new Date().getTime();

    try {
        const response = api.get<SearchResultProps[]>("/search", {
          params: {
            query: this.state.query
          }
        }).then(
          response => {
            let end = new Date().getTime();
            let duartionSeconds =  (end - start) / 1000;
            this.setState({results: response.data, isLoading: false, searchDuration: duartionSeconds,
              isNoResults: response.data.length == 0
            });
            addToSearchHistory(this.state.query);
          }
        );
    } catch (error) {
      console.error(error);
    }
  };
  
}

