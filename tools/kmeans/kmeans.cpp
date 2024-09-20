#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <tuple>
#include <opencv2/core.hpp>
#include <opencv2/core/hal/interface.h>
#include <iostream> 


int main(int argc, char** argv){

    if(argc <3){
        std::cerr << "Usage" << argv[0] << " <number_of_clusters> <input_file>" << std::endl;
        return -1;
    }

    int K = std::atoi(argv[1]);

    if(K <= 0){
        std::cerr << "Number of clusters must be greater than 0" << std::endl;
        return -1;
    }

    std::string file_path = argv[2]; 
    std::ifstream input_file(file_path);
    std::string line, dim1, dim2, dim3, dim4;
    std::vector<std::tuple<cv::Point, cv::Point>> points; 

    if(!input_file.is_open()){
        std::cerr << "Error opening input file!" << std::endl; 
        return -1; 
    }

    while(getline(input_file, line)){
        std::stringstream linestream(line);
        if(!getline(linestream, dim1, ',') || !getline(linestream, dim2, ',')
                || !getline(linestream, dim3, ',') || !getline(linestream, dim4, ',')) {
            std::cerr << "Error: Line format incorrect -> " << line << std::endl; 
            continue;        
        }
        //std::cout << x << "\t" << y << std::endl; 
        try{
            points.push_back(std::make_tuple(cv::Point(std::stol(dim1), std::stol(dim2)), cv::Point(std::stol(dim3), std::stol(dim4))));
        } catch (const std::invalid_argument& ia) {
            std::cerr << "Invalid argument: " << ia.what() << " at line -> " << line << std::endl; 
        } catch (const std::out_of_range& oor) {
            std::cerr << "Out of range: " << oor.what() << " at line -> " << line << std::endl; 
        }
        
    }

    cv::Mat cv_points(points.size(), 4, CV_32F);

    for(size_t i = 0; i < points.size(); i++){
        cv_points.at<int>(i, 0) = std::get<0>(points[i]).x; 
        cv_points.at<int>(i, 1) = std::get<0>(points[i]).y;
        cv_points.at<int>(i, 2) = std::get<1>(points[i]).x; 
        cv_points.at<int>(i, 3) = std::get<1>(points[i]).y;
    }

    //std::cout << cv_points << std::endl; 

    std::cout << "Data read succesfully. Number of points: " << points.size() << std::endl; 

    cv::Mat cv_points_scaled; 

    //cv_points.convertTo(cv_points_scaled, CV_32F, 1.0/100000);

    //std::cout << "Data scaled succesfully. Number of points: " << points.size() << std::endl; 
    
    cv::Mat labels; 
    int attempts = 5;
    cv::Mat centers; 
    cv::TermCriteria criteria(cv::TermCriteria::EPS, 10000, 0.05);

    cv::kmeans(cv_points, K, labels,
               criteria, attempts,
               cv::KMEANS_RANDOM_CENTERS, centers);

    //std::cout << "Labels: " << std::endl << labels << std::endl;
    std::cout << "Centers: " << std::endl << centers << std::endl; 

    //cv::Mat centers_scaled; 
    //centers.convertTo(centers_scaled, CV_64F, 100000); 

    //std::cout << "Centers scaled back: " << std::endl << centers_scaled << std::endl; 

    return 0;
}

